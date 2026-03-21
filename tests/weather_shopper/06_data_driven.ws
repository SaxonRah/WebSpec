# Data-driven test across both product pages

using "tests/weather_shopper/products.csv"
navigate to $page_url
wait 2 seconds
verify title contains $page_title
set $count to count of the button "Add"
log "Page: " + $page_title + " has " + $count + " products"
click the 1st button "Add"
wait 1 seconds
set $cart to text of the button containing "Cart"
log "Cart: " + $cart
take screenshot
end

log "Data-driven test complete"