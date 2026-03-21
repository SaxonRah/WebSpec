# Counter — tests repeat, variables, conditional logic

navigate to "BASE_URL"

# Verify initial state
verify the element with id "counter-value" has text "0"

# Increment 5 times
repeat 5 times
click the button "Increment"
end

verify the element with id "counter-value" has text "5"
log "Counter after 5 increments: 5"

# Decrement twice
click the button "Decrement"
click the button "Decrement"
verify the element with id "counter-value" has text "3"

# Reset
click the button "Reset"
verify the element with id "counter-value" has text "0"

# Test with extraction and conditional
repeat 3 times
click the button "Increment"
end

set $val to text of the element with id "counter-value"
log "Counter value: " + $val

take screenshot as "counter_test.png"