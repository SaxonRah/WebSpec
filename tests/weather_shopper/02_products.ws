# ══════════════════════════════════════════════════════════
# 02_products.ws — Product pages: element resolution
# Stresses: RESOLVER (fuzzy text, containing, ordinals,
# for-each, counting), PARSER (for-each, set, verify count)
# ══════════════════════════════════════════════════════════

navigate to "https://weathershopper.pythonanywhere.com/moisturizer"
wait 2 seconds

# ── Page structure verified ──────────────────────────────
verify title contains "Moisturizers"
verify the heading "Moisturizers" is visible

# ── Cart starts empty ───────────────────────────────────
verify the button containing "Cart" is visible

# ── Count product "Add" buttons ──────────────────────────
set $add_count to count of the button "Add"
log "Moisturizer Add buttons: " + $add_count

# ── Extract 1st product name and price ───────────────────
# Products are in a grid; names and prices are <p> tags
# The resolver must fuzzy-match against randomized content
set $first_name to text of the 1st element containing "Price"
log "First price element: " + $first_name

# ── Click first Add button ──────────────────────────────
click the 1st button "Add"
wait 1 seconds

# ── Cart should update from "Empty" ─────────────────────
verify the button containing "Cart" is visible
set $cart_text to text of the button containing "Cart"
log "Cart after 1 add: " + $cart_text

# ── Click second Add button ─────────────────────────────
click the 2nd button "Add"
wait 1 seconds
set $cart_text2 to text of the button containing "Cart"
log "Cart after 2 adds: " + $cart_text2

# ── Navigate to sunscreens and repeat ────────────────────
navigate to "https://weathershopper.pythonanywhere.com/sunscreen"
wait 2 seconds

verify title contains "Sunscreens"
verify the heading "Sunscreens" is visible

set $sun_count to count of the button "Add"
log "Sunscreen Add buttons: " + $sun_count

# ── Add two sunscreens ──────────────────────────────────
click the 1st button "Add"
wait 1 seconds
click the 3rd button "Add"
wait 1 seconds

set $sun_cart to text of the button containing "Cart"
log "Sunscreen cart: " + $sun_cart

take screenshot as "ws_02_products.png"
log "02_products PASSED"