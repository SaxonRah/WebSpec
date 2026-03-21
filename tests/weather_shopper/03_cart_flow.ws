# ══════════════════════════════════════════════════════════
# 03_cart_flow.ws — Add to cart and verify cart page
# Stresses: PARSER (define/call), RUNTIME (subroutines,
# multi-page nav), RESOLVER (inside, button matching)
# ══════════════════════════════════════════════════════════

define "add_moisturizers" as
    navigate to "https://weathershopper.pythonanywhere.com/moisturizer"
    wait 2 seconds
    click the 1st button "Add"
    wait 1 seconds
    click the 2nd button "Add"
    wait 1 seconds
    log "Added 2 moisturizers to cart"
end

define "add_sunscreens" as
    navigate to "https://weathershopper.pythonanywhere.com/sunscreen"
    wait 2 seconds
    click the 1st button "Add"
    wait 1 seconds
    click the 2nd button "Add"
    wait 1 seconds
    log "Added 2 sunscreens to cart"
end

define "go_to_cart" as
    click the button containing "Cart"
    wait 2 seconds
    log "Navigated to cart"
end

# ── Execute the shopping flow ────────────────────────────
call "add_moisturizers"
call "go_to_cart"

# ── Cart page assertions ────────────────────────────────
verify url contains "/cart"
verify the heading "Checkout" is visible

# ── Verify table has items ──────────────────────────────
verify the table is visible
set $cart_rows to count of the row
log "Cart rows (including header): " + $cart_rows

# ── Total price should be displayed ──────────────────────
verify the element containing "Total" is visible
set $total to text of the element containing "Total"
log "Cart total: " + $total

# ── Pay with Card button (Stripe) ───────────────────────
verify the element containing "Pay with Card" is visible

take screenshot as "ws_03_cart.png"
log "03_cart_flow PASSED"