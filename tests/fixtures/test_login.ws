# Login flow - tests forms, validation, selectors, assertions

navigate to "BASE_URL"

# Verify initial state
verify title is "WebSpec Test Site"
verify the heading "Sign In" is visible
verify the element with id "login-success" is hidden

# Test weak password validation
type "admin@test.com" into the input near "Email address"
type "short" into the input near "Password"
select "Administrator" from the dropdown near "Role"
check the checkbox near "Remember me"
check the checkbox near "I agree to the terms"
click the button "Sign In"
wait 1 seconds

# Verify error
verify the element with id "password-error" is visible
verify the element with id "password-error" contains "at least 8 characters"
take screenshot as "validation_error.png"

# Fix password and resubmit
clear the input near "Password"
type "Str0ngP@ss!" into the input near "Password"
click the button "Sign In"
wait 1 seconds

# Verify success
verify the element with id "login-success" is visible
verify the element with id "login-success" contains "successfully"
verify title contains "Dashboard"
set $page_title to title
log "Page title after login: " + $page_title
take screenshot as "login_success.png"