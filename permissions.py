STAFF_ROLES = [
    "Admin",
    "🛑Modo"
    "Admin Adjoint"
]

def is_staff(member):

    if member.guild_permissions.administrator:
        return True

    for role in member.roles:

        if role.name in STAFF_ROLES:
            return True

    return False
