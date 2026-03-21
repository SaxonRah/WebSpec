# Alerts and modal dialog flow

navigate to "BASE_URL"

# Trigger delete confirmation modal
click the button "Delete" inside the element with attr "data-user-id" is "1"
wait 1 seconds

# Verify modal appeared
verify the element with id "delete-modal" is visible
verify the element with id "delete-message" contains "Alice Johnson"

# Cancel the delete
click the button "Cancel" inside the element with id "delete-modal"
wait 1 seconds
verify the element with id "delete-modal" is hidden

# Verify row still exists
verify the element with class "user-name" containing "Alice" is visible

# Now actually delete
click the button "Delete" inside the element with attr "data-user-id" is "1"
wait 1 seconds
verify the element with id "delete-modal" is visible
click the button "Delete" inside the element with id "delete-modal"
wait 1 seconds

# Modal should close and row should be gone
verify the element with id "delete-modal" is hidden
take screenshot as "after_delete.png"