"""
WebSpec DSL - Smart Element Resolver
Uses BeautifulSoup to parse the live DOM and find elements matching
English-like selector chains, then returns Selenium-compatible locators.

Strategy:
  1. Grab page source from Selenium
  2. Parse with BS4 to get a searchable DOM
  3. Apply each selector in the chain as a progressive filter
  4. Convert the winning BS4 element to an XPath for Selenium
"""

import re
import time
from difflib import SequenceMatcher
from typing import Optional
import hashlib
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.common.by import By
import logging


from webspec_ast import ElementRef, RawElementRef, VarElementRef, Selector, VarRef, NumberLiteral, StringLiteral

logger = logging.getLogger('webspec.resolver')

# ── Tag mapping: DSL element type → HTML tags ────────────
ELEMENT_TYPE_TAGS = {
    'button':   ['button', 'input[type=submit]', 'input[type=button]',
                 'a[role=button]', '[role=button]'],
    'link':     ['a'],
    'input':    ['input', 'textarea'],
    'dropdown': ['select'],
    'checkbox': ['input[type=checkbox]'],
    'radio':    ['input[type=radio]'],
    'image':    ['img', 'svg', 'picture'],
    'heading':  ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
    'table':    ['table'],
    'row':      ['tr'],
    'cell':     ['td', 'th'],
    'field':    ['input', 'textarea', 'select'],
    'form':     ['form'],
    'section':  ['section', 'div[role=region]', 'article', 'aside'],
    'dialog':   ['dialog', '[role=dialog]', '[role=alertdialog]'],
    'menu':     ['nav', 'ul[role=menu]', '[role=menubar]', 'menu'],
    'item':     ['li', '[role=menuitem]', '[role=option]'],
    'element':  ['*'],                    # wildcard - matches anything
}


class SmartResolver:
    """Resolve DSL element references to Selenium (By, locator) tuples."""

    def __init__(self, driver, retry_timeout=5, retry_interval=0.3):
        self.driver = driver
        self._soup = None
        self._source_hash = None
        self.retry_timeout = retry_timeout
        self.retry_interval = retry_interval

    # ── Refresh the BS4 tree if the page changed ────────
    # def _refresh_soup(self):
    #     src = self.driver.page_source
    #     h = hash(src)
    #     if h != self._source_hash:
    #         self._soup = BeautifulSoup(src, 'html.parser')
    #         self._source_hash = h

    def _refresh_soup(self):
        src = self.driver.page_source
        h = hashlib.md5(src.encode('utf-8', errors='replace')).hexdigest()
        if h != self._source_hash:
            self._soup = BeautifulSoup(src, 'html.parser')
            self._source_hash = h

    # ── Public entry point ───────────────────────────────
    # def resolve(self, ref, variables=None):
    #     """
    #     Given an ElementRef, resolve with automatic retry.
    #     Retries on failure with a fresh DOM parse each attempt.
    #     """
    #     import time
    #
    #     variables = variables or {}
    #
    #     if isinstance(ref, RawElementRef):
    #         return self._resolve_raw(ref.locator)
    #
    #     # if isinstance(ref, VarElementRef):
    #     #     stored = variables.get(ref.var_name)
    #     #     if stored is None:
    #     #         raise RuntimeError(f"Variable ${ref.var_name} is not set")
    #     #     return stored
    #
    #     if isinstance(ref, VarElementRef):
    #         stored = variables.get(ref.var_name)
    #         if stored is None:
    #             raise RuntimeError(f"Variable ${ref.var_name} is not set")
    #
    #         if isinstance(stored, (list, tuple)):
    #             if not stored:
    #                 raise RuntimeError(f"Variable ${ref.var_name} is empty")
    #             stored = stored[0]
    #
    #         if not (hasattr(stored, "click") or hasattr(stored, "tag_name")):
    #             raise RuntimeError(
    #                 f"Variable ${ref.var_name} does not contain an element"
    #             )
    #         return stored
    #
    #     deadline = time.time() + self.retry_timeout
    #     # last_error = None
    #
    #     while True:
    #         try:
    #             # self._refresh_soup(force=(last_error is not None)) ???
    #             self._refresh_soup()
    #             candidates = self._get_candidates(ref.elem_type)
    #             candidates = self._apply_selectors(
    #                 candidates, ref.selectors, variables)
    #
    #             if not candidates:
    #                 raise RuntimeError(
    #                     f"No element found for: the {ref.elem_type} "
    #                     f"with {len(ref.selectors)} selector(s)"
    #                 )
    #
    #             # idx = (ref.ordinal or 1) - 1
    #             # if idx >= len(candidates):
    #             #     raise RuntimeError(
    #             #         f"Requested {ref.ordinal}th match but only "
    #             #         f"{len(candidates)} found"
    #             #     )
    #
    #             idx = 0 if ref.ordinal is None else ref.ordinal - 1
    #             if idx < 0:
    #                 raise RuntimeError(
    #                     f"Ordinal must be >= 1, got {ref.ordinal}"
    #                 )
    #             if idx >= len(candidates):
    #                 raise RuntimeError(
    #                     f"Requested {ref.ordinal}th match but only "
    #                     f"{len(candidates)} found"
    #                 )
    #
    #             chosen = candidates[idx]
    #             xpath = self._tag_to_xpath(chosen)
    #             return self.driver.find_element(By.XPATH, xpath)
    #
    #         except Exception: # as e:
    #             # last_error = e
    #             if time.time() >= deadline:
    #                 raise
    #             time.sleep(self.retry_interval)


    def resolve(self, ref, variables=None):
        variables = variables or {}

        if isinstance(ref, RawElementRef):
            return self._resolve_raw(ref.locator)

        if isinstance(ref, VarElementRef):
            stored = variables.get(ref.var_name)
            if stored is None:
                raise RuntimeError(f"Variable ${ref.var_name} is not set")
            if isinstance(stored, (list, tuple)):
                if not stored:
                    raise RuntimeError(f"Variable ${ref.var_name} is empty")
                stored = stored[0]
            if not (hasattr(stored, "click") or hasattr(stored, "tag_name")):
                raise RuntimeError(
                    f"Variable ${ref.var_name} does not contain an element"
                )
            return stored

        deadline = time.time() + self.retry_timeout
        last_error = None
        attempts = 0

        while True:
            try:
                # Raw refs now get retry too
                if isinstance(ref, RawElementRef):
                    return self._resolve_raw(ref.locator)

                self._refresh_soup()
                candidates = self._get_candidates(ref.elem_type)
                candidates = self._apply_selectors(
                    candidates, ref.selectors, variables)

                if not candidates:
                    raise RuntimeError(
                        f"No element found for: the {ref.elem_type} "
                        f"with {len(ref.selectors)} selector(s)"
                    )

                idx = 0 if ref.ordinal is None else ref.ordinal - 1
                if idx >= len(candidates):
                    raise RuntimeError(
                        f"Requested {ref.ordinal}th match but only "
                        f"{len(candidates)} found"
                    )

                chosen = candidates[idx]
                xpath = self._tag_to_xpath(chosen)
                return self.driver.find_element(By.XPATH, xpath)

            except Exception as e:
                last_error = e
                attempts += 1
                if time.time() >= deadline:
                    logger.debug(
                        f"Resolve failed after {attempts} attempts: {last_error}"
                    )
                    raise last_error
                time.sleep(self.retry_interval)


    def resolve_all(self, ref, variables=None):
        """Return ALL matching elements as Selenium WebElements."""
        variables = variables or {}
        deadline = time.time() + self.retry_timeout
        last_error = None

        while True:
            try:
                self._refresh_soup()

                if isinstance(ref, RawElementRef):
                    if ref.locator.startswith('/') or ref.locator.startswith('('):
                        return self.driver.find_elements(By.XPATH, ref.locator)
                    return self.driver.find_elements(By.CSS_SELECTOR, ref.locator)

                if isinstance(ref, VarElementRef):
                    stored = variables.get(ref.var_name)
                    if stored is None:
                        raise RuntimeError(f"Variable ${ref.var_name} is not set")
                    if isinstance(stored, list):
                        return stored
                    if isinstance(stored, tuple):
                        return list(stored)
                    return [stored]

                candidates = self._get_candidates(ref.elem_type)
                candidates = self._apply_selectors(candidates, ref.selectors, variables)

                results = []
                for tag in candidates:
                    xpath = self._tag_to_xpath(tag)
                    try:
                        results.append(self.driver.find_element(By.XPATH, xpath))
                    except Exception:
                        continue
                return results

            except Exception as e:
                last_error = e
                if time.time() >= deadline:
                    raise last_error
                time.sleep(self.retry_interval)

    # def resolve_all(self, ref, variables=None):
    #     """Return ALL matching elements as Selenium WebElements."""
    #     variables = variables or {}
    #     deadline = time.time() + self.retry_timeout
    #     last_error = None
    #
    #     while True:
    #         try:
    #             self._refresh_soup()
    #             candidates = self._get_candidates(ref.elem_type)
    #             candidates = self._apply_selectors(candidates, ref.selectors, variables)
    #
    #             results = []
    #             for tag in candidates:
    #                 xpath = self._tag_to_xpath(tag)
    #                 try:
    #                     results.append(self.driver.find_element(By.XPATH, xpath))
    #                 except Exception:
    #                     continue
    #
    #             return results
    #
    #         except Exception as e:
    #             last_error = e
    #             if time.time() >= deadline:
    #                 raise last_error
    #             time.sleep(self.retry_interval)

    # ── Variable interpolation ───────────────────────────
    @staticmethod
    def _interpolate(value, variables):
        """Replace ${varname} placeholders with runtime variable values."""
        if '$' not in value:
            return value

        def _replace_braced(match):
            name = match.group(1)
            resolved = variables.get(name)
            if resolved is None:
                raise RuntimeError(f"Variable ${name} used in selector but not set")
            if hasattr(resolved, 'text'):
                return resolved.text
            return str(resolved)

        def _replace_unbraced(match):
            name = match.group(1)
            resolved = variables.get(name)
            if resolved is None:
                raise RuntimeError(f"Variable ${name} used in selector but not set")
            if hasattr(resolved, 'text'):
                return resolved.text
            return str(resolved)

        value = re.sub(r'\$\{(\w+)}', _replace_braced, value)
        value = re.sub(r'(?<!\$)\$(\w+)', _replace_unbraced, value)
        return value

    # ── Resolve raw CSS / XPath ──────────────────────────
    def _resolve_raw(self, locator):
        if locator.startswith('/') or locator.startswith('('):
            return self.driver.find_element(By.XPATH, locator)
        return self.driver.find_element(By.CSS_SELECTOR, locator)

    # ── Get initial candidates by element type ───────────
    def _get_candidates(self, elem_type):
        tag_specs = ELEMENT_TYPE_TAGS.get(elem_type, ['*'])
        candidates = []
        for spec in tag_specs:
            if '[' in spec:
                # e.g. 'input[type=checkbox]' or '[role=button]'
                tag_name, attr_part = (
                    spec.split('[', 1) if not spec.startswith('[')
                    else ('', spec[1:])
                )
                attr_part = attr_part.rstrip(']')
                attr_name, attr_val = attr_part.split('=', 1)
                kwargs = {attr_name: attr_val}
                if tag_name:
                    candidates += self._soup.find_all(tag_name, attrs=kwargs)
                else:
                    candidates += self._soup.find_all(attrs=kwargs)
            else:
                if spec == '*':
                    candidates += self._soup.find_all(True)
                else:
                    candidates += self._soup.find_all(spec)
        # Deduplicate preserving order
        seen = set()
        unique = []
        for c in candidates:
            cid = id(c)
            if cid not in seen:
                seen.add(cid)
                unique.append(c)
        return unique

    # ── Apply selector chain as progressive filters ──────
    def _apply_selectors(self, candidates, selectors, variables):
        for sel in selectors:
            candidates = self._apply_one(candidates, sel, variables)
            if not candidates:
                break
        return candidates

    def _stringify_runtime_value(self, value):
        if isinstance(value, StringLiteral):
            return value.value
        if isinstance(value, NumberLiteral):
            return str(value.value)
        if isinstance(value, VarRef):
            raise RuntimeError("VarRef reached SmartResolver before runtime evaluation")
        if value is None:
            return ""
        return str(value)

    def _apply_one(self, candidates, sel: Selector, variables):
        kind = sel.kind

        # Resolve any ${variable} references in selector values
        # value = self._interpolate(sel.value, variables) if sel.value else ''
        # extra = self._interpolate(sel.extra, variables) if sel.extra else ''
        tvalue = self._stringify_runtime_value(sel.value) if sel.value is not None else ''
        textra = self._stringify_runtime_value(sel.extra) if sel.extra is not None else ''
        value = self._interpolate(tvalue, variables) if tvalue else ''
        extra = self._interpolate(textra, variables) if textra else ''

        if kind == 'text':
            return self._filter_fuzzy_text(candidates, value)

        elif kind == 'with_text':
            return [c for c in candidates
                    if c.get_text(strip=True) == value]

        elif kind == 'class':
            return [c for c in candidates
                    if value in (c.get('class') or [])]

        elif kind == 'id':
            return [c for c in candidates
                    if c.get('id') == value]

        elif kind == 'attr':
            return [c for c in candidates
                    if c.get(extra) == value]

        elif kind == 'placeholder':
            v = self._stringify_runtime_value(value).lower()
            return [
                c for c in candidates
                if c.get('placeholder', '').lower() == v
            ]

        elif kind == 'value':
            v = self._stringify_runtime_value(value)
            return [c for c in candidates
                    if c.get('value', '') == v]

        elif kind == 'containing':
            v = self._stringify_runtime_value(value).lower()
            return [
                c for c in candidates
                if v in c.get_text(strip=True).lower()
            ]

        elif kind == 'matching':
            pattern_text = self._stringify_runtime_value(value)
            try:
                pattern = re.compile(pattern_text)
            except re.error as e:
                raise RuntimeError(f"Invalid regex /{pattern_text}/: {e}") from e

            return [
                c for c in candidates
                if pattern.search(c.get_text(strip=True))
            ]

        elif kind == 'near':
            matches = self._filter_near_label(candidates, value)
            if not matches:
                raise RuntimeError(f'No elements found near label "{self._stringify_runtime_value(value)}"')
            return matches

        elif kind == 'inside':
            parent_el = self._resolve_bs4(sel.child, variables)
            if not parent_el:
                return []
            return [c for c in candidates if c in parent_el.descendants]

        elif kind in ('above', 'below', 'after', 'before'):
            return self._filter_spatial(candidates, sel, variables)

        return candidates

    # ── Fuzzy text matching ──────────────────────────────
    @staticmethod
    def _filter_fuzzy_text(candidates, query):
        """
        Match by: exact text, aria-label, title, placeholder,
        value, alt - then fall back to fuzzy ratio.
        """
        query_lower = query.lower().strip()
        exact, partial, fuzzy = [], [], []

        for c in candidates:
            texts = [
                c.get_text(strip=True),
                c.get('aria-label', ''),
                c.get('title', ''),
                c.get('placeholder', ''),
                c.get('value', ''),
                c.get('alt', ''),
            ]
            texts_lower = [t.lower().strip() for t in texts if t]

            if query_lower in texts_lower:
                exact.append(c)
            elif any(query_lower in t for t in texts_lower):
                partial.append(c)
            else:
                best = max(
                    (SequenceMatcher(None, query_lower, t).ratio()
                     for t in texts_lower),
                    default=0
                )
                if best > 0.6:
                    fuzzy.append((best, c))

        if exact:
            return exact
        if partial:
            return partial
        fuzzy.sort(key=lambda x: -x[0])
        return [c for _, c in fuzzy]

    # ── "near" - find elements close to a label ──────────
    def _filter_near_label(self, candidates, label_text):
        """
        Find a label / text node matching label_text, then return
        candidates that are siblings, adjacent, or share a parent
        with that label - simulating spatial proximity.

        Resolution order (most reliable first):
          1. <label for="..."> with matching text → target by id
          2. Exact text match on label-like elements → DOM proximity
          3. Partial text match on label-like elements → DOM proximity
          4. Direct-text match on broader elements → DOM proximity
          5. aria-label on nearby containers → DOM proximity
        """
        label_text = self._stringify_runtime_value(label_text)
        label_lower = label_text.lower().strip()
        # label_lower = label_text.lower().strip()

        # ── Strategy 1: <label for="..."> (most reliable) ────
        for lb in self._soup.find_all('label'):
            lb_text = lb.get_text(strip=True).lower()
            if lb.get('for') and (
                lb_text == label_lower or label_lower in lb_text
            ):
                target_id = lb['for']
                matches = [c for c in candidates
                           if c.get('id') == target_id]
                if matches:
                    return matches

        # ── Strategy 2: Exact text on label-like tags ─────────
        label_tags = ['label', 'legend', 'dt', 'th']
        for lb in self._soup.find_all(label_tags):
            if lb.get_text(strip=True).lower() == label_lower:
                nearby = self._get_nearby_tags(lb)
                matches = [c for c in candidates if id(c) in nearby]
                if matches:
                    return matches

        # ── Strategy 3: Partial text on label-like tags ───────
        for lb in self._soup.find_all(label_tags):
            if label_lower in lb.get_text(strip=True).lower():
                nearby = self._get_nearby_tags(lb)
                matches = [c for c in candidates if id(c) in nearby]
                if matches:
                    return matches

        # ── Strategy 4: Broader search with direct-text check ─
        broad_tags = ['span', 'p', 'div', 'h1', 'h2', 'h3',
                      'h4', 'h5', 'h6']
        for lb in self._soup.find_all(broad_tags):
            direct_texts = lb.find_all(string=True, recursive=False)
            own_text = ' '.join(t.strip() for t in direct_texts).lower()
            if label_lower in own_text:
                nearby = self._get_nearby_tags(lb)
                matches = [c for c in candidates if id(c) in nearby]
                if matches:
                    return matches

        # ── Strategy 5: aria-label on nearby containers ───────
        for el in self._soup.find_all(True):
            aria = el.get('aria-label', '').lower()
            if label_lower in aria:
                nearby = self._get_nearby_tags(el)
                matches = [c for c in candidates if id(c) in nearby]
                if matches:
                    return matches

        # return candidates  # can't narrow - return all
        return []

    @staticmethod
    def _get_nearby_tags(element):
        """
        Return set of tag ids near the given element.
        Only walks up ONE ancestor level to avoid the
        'everything is nearby' problem.
        """
        nearby = set()

        # The element itself and its descendants
        nearby.add(id(element))
        for desc in element.descendants:
            if isinstance(desc, Tag):
                nearby.add(id(desc))

        # Siblings and their descendants (same parent)
        if element.parent:
            for sib in element.parent.children:
                if isinstance(sib, Tag):
                    nearby.add(id(sib))
                    for desc in sib.descendants:
                        if isinstance(desc, Tag):
                            nearby.add(id(desc))

        # One level up: grandparent's children and their descendants
        if element.parent and element.parent.parent:
            gp = element.parent.parent
            for child in gp.children:
                if isinstance(child, Tag):
                    nearby.add(id(child))
                    for desc in child.descendants:
                        if isinstance(desc, Tag):
                            nearby.add(id(desc))

        return nearby

    # ── Spatial filtering (above/below/after/before) ─────
    def _filter_spatial(self, candidates, sel, variables):
        """
        Uses document order as a proxy for spatial position.
        above/before → candidate appears before the anchor
        below/after  → candidate appears after the anchor
        """
        anchor = self._resolve_bs4(sel.child, variables)
        if not anchor:
            return candidates

        all_tags = list(self._soup.find_all(True))
        try:
            anchor_idx = next(i for i, t in enumerate(all_tags)
                             if t is anchor)
        except StopIteration:
            return candidates

        if sel.kind in ('above', 'before'):
            valid_ids = {id(t) for i, t in enumerate(all_tags)
                         if i < anchor_idx}
        else:
            valid_ids = {id(t) for i, t in enumerate(all_tags)
                         if i > anchor_idx}

        return [c for c in candidates if id(c) in valid_ids]

    def _filter_spatial_real(self, candidates, sel, variables):
        anchor_tag = self._resolve_bs4(sel.child, variables)
        if not anchor_tag:
            return candidates

        anchor_el = self.driver.find_element(By.XPATH, self._tag_to_xpath(anchor_tag))
        ar = anchor_el.rect

        out = []
        for cand in candidates:
            try:
                el = self.driver.find_element(By.XPATH, self._tag_to_xpath(cand))
                cr = el.rect

                if sel.kind == 'above' and cr['y'] + cr['height'] <= ar['y']:
                    out.append(cand)
                elif sel.kind == 'below' and cr['y'] >= ar['y'] + ar['height']:
                    out.append(cand)
                elif sel.kind == 'before' and cr['x'] + cr['width'] <= ar['x']:
                    out.append(cand)
                elif sel.kind == 'after' and cr['x'] >= ar['x'] + ar['width']:
                    out.append(cand)
            except Exception:
                pass

        return out

    # ── Resolve an element ref purely in BS4 ─────────────
    def _resolve_bs4(self, ref, variables) -> Optional[Tag]:
        if isinstance(ref, ElementRef):
            cands = self._get_candidates(ref.elem_type)
            cands = self._apply_selectors(cands, ref.selectors, variables)
            return cands[0] if cands else None
        return None

    # ── Convert a BS4 Tag to a unique XPath ──────────────
    @staticmethod
    def _tag_to_xpath(tag: Tag) -> str:
        """
        Build an absolute XPath from a BS4 tag by walking up
        the tree and computing sibling indices.
        """
        parts = []
        current = tag
        while current and current.name and current.name != '[document]':
            siblings = [
                s for s in (current.parent.children if current.parent
                            else [])
                if isinstance(s, Tag) and s.name == current.name
            ]
            if len(siblings) > 1:
                idx = siblings.index(current) + 1
                parts.append(f'{current.name}[{idx}]')
            else:
                parts.append(current.name)
            current = current.parent

        parts.reverse()
        return '/' + '/'.join(parts)