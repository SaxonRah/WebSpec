# Table iteration — tests for-each, inside, try-catch, dynamic state

navigate to "BASE_URL"

# Verify table exists
verify the table is visible
set $row_count to count of the row inside the element "tbody"
log "Data rows: " + $row_count

# Check specific cell content
verify the 1st element with class "user-name" has text "Alice Johnson"
verify the 1st element with class "status" has text "active"

# Find inactive users and activate them
set $inactive_count to count of the element with class "status-inactive"
log "Inactive users: " + $inactive_count

# Click activate on Carol (3rd row, which has an Activate button)
click the button "Activate" inside the element with attr "data-user-id" is "3"
wait 1 seconds

# Verify activation worked
set $new_inactive to count of the element with class "status-inactive"
log "Inactive after activation: " + $new_inactive

# Test delete modal
click the button "Delete" inside the element with attr "data-user-id" is "2"
wait 1 seconds
verify the element with id "delete-modal" is visible
verify the element with id "delete-message" contains "Bob Smith"

# Cancel the delete
click the button "Cancel" inside the element with id "delete-modal"
wait 1 seconds
verify the element with id "delete-modal" is hidden

take screenshot as "table_test.png"