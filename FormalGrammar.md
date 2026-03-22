```
# ══════════════════════════════════════════════════════════
# WebSpec DSL - Complete Grammar (v1.0 final)
# 182 production rules - 383 LALR states - 0 reduce/reduce
# ══════════════════════════════════════════════════════════

── Program ─────────────────────────────────────────────────
program          → newlines statement_list
                 | statement_list
                 | newlines
                 | ε

newlines         → NEWLINE
                 | newlines NEWLINE

statement_list   → statement
                 | statement_list NEWLINE statement
                 | statement_list NEWLINE

statement        → nav_stmt | action_stmt | assertion_stmt
                 | wait_stmt | var_stmt | control_stmt
                 | log_stmt | screenshot_stmt | alert_stmt
                 | frame_stmt | window_stmt | extract_stmt
                 | import_stmt

── Navigation ──────────────────────────────────────────────
nav_stmt         → NAVIGATE TO expr
                 | GO BACK | GO FORWARD | REFRESH
                 | SWITCH TO TAB NUMBER

── Element References (the smart-find core) ────────────────
element_ref      → THE elem_type selector_chain
                 | THE ORDINAL elem_type selector_chain
                 | THE ORDINAL elem_type
                 | THE elem_type
                 | ELEMENT STRING                   /* raw css/xpath */
                 | VARIABLE

elem_type        → BUTTON | LINK | INPUT | DROPDOWN | CHECKBOX
                 | RADIO | IMAGE | HEADING | TABLE
                 | ROW | CELL | ELEMENT | FIELD | FORM | SECTION
                 | DIALOG | MENU | ITEM

── Selector Chains ────────────────────────────────────────
selector_chain   → selector
                 | selector_chain selector

text_value       → STRING | VARIABLE

selector         → text_value                       /* fuzzy text match */
                 | WITH CLASS text_value
                 | WITH ID text_value
                 | WITH TEXT text_value
                 | WITH ATTR text_value IS text_value
                 | WITH PLACEHOLDER text_value
                 | WITH VALUE text_value
                 | CONTAINING text_value
                 | MATCHING text_value              /* regex */
                 | NEAR text_value
                 | INSIDE element_ref
                 | ABOVE element_ref
                 | BELOW element_ref
                 | AFTER element_ref
                 | BEFORE element_ref

── Actions ─────────────────────────────────────────────────
action_stmt      → CLICK element_ref
                 | DOUBLE CLICK element_ref
                 | RIGHT CLICK element_ref
                 | TYPE expr INTO element_ref
                 | APPEND expr TO element_ref
                 | CLEAR element_ref
                 | SELECT STRING FROM element_ref
                 | CHECK element_ref
                 | UNCHECK element_ref
                 | TOGGLE element_ref
                 | HOVER element_ref
                 | FOCUS element_ref
                 | SCROLL TO element_ref
                 | SCROLL DOWN NUMBER PIXELS
                 | SCROLL UP NUMBER PIXELS
                 | DRAG element_ref TO element_ref
                 | PRESS KEY STRING
                 | PRESS KEY STRING WITH STRING      /* modifier keys */
                 | UPLOAD STRING TO element_ref
                 | SUBMIT element_ref
                 | EXECUTE STRING                   /* raw JS */

── Assertions ──────────────────────────────────────────────
assertion_stmt   → VERIFY element_ref IS visibility
                 | VERIFY element_ref HAS TEXT string_or_var
                 | VERIFY element_ref CONTAINS string_or_var
                 | VERIFY element_ref MATCHES string_or_var
                 | VERIFY element_ref HAS ATTR STRING eq_op STRING
                 | VERIFY element_ref HAS CLASS STRING
                 | VERIFY element_ref HAS STYLE STRING eq_op STRING
                 | VERIFY element_ref COUNT comparator NUMBER
                 | VERIFY URL eq_op string_or_var
                 | VERIFY TITLE eq_op string_or_var
                 | VERIFY COOKIE STRING eq_op STRING
                 | VERIFY DOWNLOADED STRING
                 | VERIFY ALERT HAS TEXT STRING

string_or_var    → STRING | VARIABLE

visibility       → VISIBLE | HIDDEN | ENABLED | DISABLED
                 | SELECTED | CHECKED | EMPTY | FOCUSED

comparator       → IS | EQUALS
                 | GREATER THAN | LESS THAN

eq_op            → IS | EQUALS
                 | CONTAINS | CONTAINING
                 | MATCHES
                 | STARTS WITH | ENDS WITH

── Waits ───────────────────────────────────────────────────
wait_stmt        → WAIT NUMBER SECONDS
                 | WAIT FOR element_ref
                 | WAIT FOR element_ref TO BE visibility
                 | WAIT UP TO NUMBER SECONDS FOR element_ref
                 | WAIT UNTIL URL CONTAINS STRING
                 | WAIT UNTIL TITLE CONTAINS STRING

── Variables & Expressions ─────────────────────────────────
var_stmt         → SET VARIABLE TO expr
                 | SET VARIABLE TO TEXT OF element_ref
                 | SET VARIABLE TO ATTR STRING OF element_ref
                 | SET VARIABLE TO VALUE OF element_ref
                 | SET VARIABLE TO COUNT OF element_ref
                 | SET VARIABLE TO URL
                 | SET VARIABLE TO TITLE

expr             → STRING
                 | NUMBER
                 | VARIABLE
                 | expr PLUS expr
                 | LPAREN expr RPAREN

── Control Flow ────────────────────────────────────────────
control_stmt     → IF condition THEN NL statement_list END
                 | IF condition THEN NL stmt_list ELSE NL stmt_list END
                 | REPEAT NUMBER TIMES NL statement_list END
                 | REPEAT WHILE condition NL statement_list END
                 | FOR EACH element_ref AS VARIABLE DO NL stmt_list END
                 | FOR EACH element_ref AS VARIABLE NL stmt_list END
                 | TRY NL statement_list ON ERROR NL stmt_list END
                 | CALL STRING
                 | DEFINE STRING AS NL statement_list END
                 | USING STRING NL statement_list END

condition        → element_ref IS visibility
                 | expr comparator expr
                 | VARIABLE IS visibility
                 | VARIABLE IS STRING
                 | VARIABLE IS NUMBER
                 | VARIABLE IS VARIABLE
                 | VARIABLE EQUALS STRING
                 | VARIABLE EQUALS NUMBER
                 | VARIABLE EQUALS VARIABLE
                 | VARIABLE GREATER THAN STRING
                 | VARIABLE GREATER THAN NUMBER
                 | VARIABLE GREATER THAN VARIABLE
                 | VARIABLE LESS THAN STRING
                 | VARIABLE LESS THAN NUMBER
                 | VARIABLE LESS THAN VARIABLE
                 | URL CONTAINS STRING
                 | NOT condition
                 | condition AND condition
                 | condition OR condition
                 | LPAREN condition RPAREN

── Misc ────────────────────────────────────────────────────
log_stmt         → LOG expr

screenshot_stmt  → TAKE SCREENSHOT
                 | TAKE SCREENSHOT AS STRING

alert_stmt       → ACCEPT ALERT
                 | DISMISS ALERT
                 | VERIFY ALERT HAS TEXT STRING

frame_stmt       → SWITCH TO FRAME element_ref
                 | SWITCH TO FRAME STRING
                 | SWITCH TO DEFAULT FRAME

window_stmt      → SWITCH TO WINDOW STRING
                 | OPEN NEW WINDOW
                 | CLOSE WINDOW

extract_stmt     → SAVE SOURCE AS STRING
                 | SAVE COOKIES AS STRING

import_stmt      → IMPORT STRING

── Precedence (lowest to highest) ──────────────────────────
                   OR          (left)
                   AND         (left)
                   NOT         (right)
                   PLUS        (left)
```
