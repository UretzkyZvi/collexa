package collexa.authz.invoke

import rego.v1

# Default deny
default allow := false

# Allow if user is owner of the organization
allow if {
    input.user.id
    input.org.id
    user_is_org_owner
}

# Allow if user has explicit permission for this capability
allow if {
    input.user.id
    input.agent.id
    input.capability
    user_has_capability_permission
}

# Allow if this is a read-only capability (starts with "get" or "list")
allow if {
    input.capability
    is_read_only_capability
}

# Helper rules
user_is_org_owner if {
    # In a real implementation, this would check user roles
    # For now, allow if user_id matches a pattern or is in data
    input.user.id == data.org_owners[input.org.id]
}

user_has_capability_permission if {
    # Check if user has explicit permission for this capability
    permissions := data.user_permissions[input.user.id]
    permissions[input.capability] == true
}

is_read_only_capability if {
    startswith(input.capability, "get")
}

is_read_only_capability if {
    startswith(input.capability, "list")
}

is_read_only_capability if {
    startswith(input.capability, "read")
}
