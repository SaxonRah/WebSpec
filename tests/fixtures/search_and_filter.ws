# E-commerce search flow

navigate to "BASE_URL"

# Search for a product
type "wireless headphones" into the input with placeholder "Search products..."
click the button "Search"
wait 1 seconds
verify the element with id "search-results" is visible

# Apply filters
click the button "Filters"
wait 1 seconds
check the checkbox near "Noise Cancelling"
select "Price: Low to High" from the dropdown near "Sort by"

# Verify results
verify the element with class "product-card" count greater than 0
set $count to count of the element with class "product-card"
log "Found " + $count + " products"

# Inspect first result
set $title to text of the 1st element with class "product-title"
set $price to text of the 1st element with class "product-price"
log "First product: " + $title + " at " + $price
take screenshot as "search_results.png"