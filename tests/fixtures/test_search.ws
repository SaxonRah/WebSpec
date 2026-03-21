# Search & filter — tests dynamic visibility, counting, extraction

navigate to "BASE_URL"

# Search for products
type "wireless headphones" into the input with placeholder "Search products..."
click the button "Search"
wait 1 seconds

# Verify results appeared
verify the element with id "search-results" is visible
verify the heading with id "results-heading" contains "wireless headphones"

# Open filters
click the button "Filters"
wait 1 seconds
verify the element with id "filter-panel" is visible

# Apply filter
check the checkbox near "Noise Cancelling"
select "Price: Low to High" from the dropdown near "Sort by"

# Count products
verify the element with class "product-card" count greater than 0
set $count to count of the element with class "product-card"
log "Found " + $count + " products"

# Extract first product info
set $title to text of the 1st element with class "product-title"
set $price to text of the 1st element with class "product-price"
log "First product: " + $title + " at " + $price

# Verify specific product
verify the 1st element with class "product-title" has text "Wireless Pro Headphones"
verify the 1st element with class "product-price" has text "$79.99"

take screenshot as "search_results.png"