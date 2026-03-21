# Basic login flow

navigate to "BASE_URL"

type "admin@test.com" into the input near "Email address"
type "secret123" into the input near "Password"
click the button "Sign In"

wait 1 seconds
verify the element with id "password-error" is hidden
verify the element with id "login-success" is visible
verify title contains "Dashboard"
take screenshot as "login_success.png"