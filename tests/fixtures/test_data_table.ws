# Data table with variable comparison — tests the $var is "string" fix

navigate to "BASE_URL"

verify the table is visible

# Iterate rows and check status using variable comparison
for each the row inside the element "tbody" as $row
    try
        set $name to text of the element with class "user-name" inside $row
        set $status to text of the element with class "status" inside $row
        log "User: " + $name + " Status: " + $status
        if $status is "inactive" then
            log "Found inactive user: " + $name
        end
    on error
        log "Skipping row: " + $_error
    end
end

take screenshot as "data_table_test.png"