const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function buildSandbox() {
  const sandbox = {
    window: {},
    document: {
      addEventListener() {},
      querySelector() {
        return null;
      },
      querySelectorAll() {
        return [];
      },
    },
    location: { href: "https://example.com/app" },
    setInterval() { return 1; },
    clearInterval() {},
    setTimeout(fn) { return 1; },
    clearTimeout() {},
    console,
  };

  sandbox.window.addEventListener = function () {};
  sandbox.window.scrollY = 0;

  return sandbox;
}

function loadRecorder() {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "webspec_capture.js"),
    "utf8"
  );
  const sandbox = buildSandbox();
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox);
  return sandbox;
}

function makeElement(tagName, attrs = {}) {
  return {
    tagName,
    id: attrs.id || "",
    childNodes: [],
    textContent: attrs.textContent || "",
    parentElement: null,
    previousElementSibling: null,
    getAttribute(name) {
      return attrs[name] || null;
    },
  };
}

(function test_checkbox_context_returns_checkbox() {
  const sandbox = loadRecorder();
  const el = makeElement("INPUT", { type: "checkbox" });

  sandbox.document.querySelectorAll = function () {
    return [el];
  };

  const ctx = sandbox.window.__webspec_recorder._getContext(el);
  assert.strictEqual(ctx.elemType, "checkbox");
})();

(function test_radio_context_returns_radio() {
  const sandbox = loadRecorder();
  const el = makeElement("INPUT", { type: "radio" });

  sandbox.document.querySelectorAll = function () {
    return [el];
  };

  const ctx = sandbox.window.__webspec_recorder._getContext(el);
  assert.strictEqual(ctx.elemType, "radio");
})();

console.log("capture tests passed");

// find way for pytest to kick off this
// node tests/test_capture.js