# Full flow — define/call subroutines, form validation, multi-step

navigate to "BASE_URL"

define "fill_login" as
    type "admin@test.com" into the input near "Email address"
    type "short" into the input near "Password"
    select "Editor" from the dropdown near "Role"
    check the checkbox near "I agree to the terms"
end

# Test 1: Submit with weak password
call "fill_login"
click the button "Sign In"
wait 1 seconds
verify the element with id "password-error" is visible
take screenshot as "weak_password.png"

# Test 2: Fix and resubmit
clear the input near "Password"
type "Str0ngP@ss!2024" into the input near "Password"
click the button "Sign In"
wait 1 seconds
verify the element with id "login-success" is visible
verify title contains "Dashboard"

# Test 3: Search products
type "headphones" into the input with placeholder "Search products..."
click the button "Search"
wait 1 seconds
verify the element with id "search-results" is visible
verify the element with class "product-card" count greater than 0

# Test 4: Counter
repeat 3 times
click the button "Increment"
end
verify the element with id "counter-value" has text "3"

log "Full flow complete"
take screenshot as "full_flow_done.png"