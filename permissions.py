import os
import ntsecuritycon as nt
import win32security
import pathlib as path



PERMISSION_HIERARCH ={
    "Full Control": nt.FILE_ALL_ACCESS,
    "Modify": (nt.FILE_GENERIC_EXECUTE| nt.FILE_DELETE_CHILD| nt.FILE_GENERIC_READ | nt.FILE_GENERIC_WRITE ),
    "Read & Execute": nt.FILE_GENERIC_READ | nt.FILE_GENERIC_EXECUTE,
    "Write": nt.FILE_GENERIC_WRITE,
    "Read": nt.FILE_GENERIC_READ,
}


security_descriptor_cache = {}

# Evaluates the mask and determines the permission
def determine_hierarch(mask):
    # print(f"Debug: Determining permission for mask: {hex(mask)}")

    # Check Full Control first
    if mask == PERMISSION_HIERARCH["Full Control"]:
        return "Full Control"

    # Check Modify
    modify_mask = PERMISSION_HIERARCH["Modify"]
    if (mask == modify_mask) or (mask == 0x1301bf):
        return "Modify"

    # Check Read & Execute
    read_execute_mask = PERMISSION_HIERARCH["Read & Execute"]
    if (mask & read_execute_mask) == read_execute_mask:
        return "Read & Execute"

    # If no standard permissions
    specific = []

    for permission_type in ["Read", "Write", "Execute", "Delete"]:
        match permission_type:
            case "Read":
                if mask & nt.FILE_GENERIC_READ == nt.FILE_GENERIC_READ:
                    specific.append("Read")
            case "Write":
                if mask & nt.FILE_GENERIC_WRITE == nt.FILE_GENERIC_WRITE:
                    specific.append("Write")
            case "Execute":
                if mask & nt.FILE_GENERIC_EXECUTE == nt.FILE_GENERIC_EXECUTE:
                    specific.append("Execute")
            case "Delete":
                if mask & nt.FILE_DELETE_CHILD == nt.FILE_DELETE_CHILD:
                    specific.append("Delete")

    permission = " + ".join(specific) if specific else "Special"

    return permission

# List the permission for the provided folder path m
def get_all_principal_permission(file_path):
    try:
        security_reader = win32security.GetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION)
        dacl = security_reader.GetSecurityDescriptorDacl()
        if dacl is None:
            return [("Error", "No DACL found", "")]

        security_permission = []

        encountered_principal_sources = set()

        # Loop through Access Control Entry, -List of whom and what they have permissions to.
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            ace_flags = ace[0][1]
            mask = ace[1]  # Shows if read,write...
            sid = ace[2]  # User in that row

            # SID is DOMAIN\User
            try:
                user, domain, _ = win32security.LookupAccountSid(None, sid)
                account = f"{domain}\\{user}"
            except win32security.error:
                account = f"Unknown SID: {sid}"
            # categorize mask
            perms = determine_hierarch(mask)

            permission = "".join(perms)

            # Checks inherited or None
            if ace_flags & win32security.INHERITED_ACE:
                source = get_inheritance_source(file_path, sid,mask)
            else:
                source = "Set Here"

            if (account,source) in encountered_principal_sources:
                source = "SHOULD BE BLANK HERE"
            else:
                encountered_principal_sources.add((account,source))

            #Checks what the permissions are applied to
            type_path_permission = check_inheritance_type(ace_flags)

            security_permission.append((account, permission, source,type_path_permission))

        return security_permission

    except Exception as e:
        return [("Error", str(e), "")]

# List the permission for the provided folder path and user
def get_user_permissions_only(file_path):
    try:
        # Retrieve the security descriptor for the given file
        security_reader = get_cached_security_descriptor(file_path)
        dacl = security_reader.GetSecurityDescriptorDacl()

        if dacl is None:
            return [("Error", "No DACL found", "")]

        user_permissions = []

        # Use a set to track encountered (account, source) pairs
        encountered_principal_sources = set()

        # Loop through all Access Control Entries (ACE)
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            ace_flags = ace[0][1]
            #print(F" {ace_flags}")
            mask = ace[1]  # Access mask (permissions)
            sid = ace[2]  # Security Identifier (SID)

            # Check only for "User" principals
            principal_type = get_principal_type(sid)
            if principal_type == "User":  # Only process users
                try:
                    # Retrieve DOMAIN\USERNAME from SID
                    user, domain, _ = win32security.LookupAccountSid(None, sid)
                    account = f"{domain}\\{user}"
                except win32security.error:
                    account = f"Unknown SID: {sid}"

                # Determine categorized permissions based on mask
                perms = determine_hierarch(mask)
                permission = "".join(perms)

                # Check for inheritance flags
                if ace_flags & win32security.INHERITED_ACE:
                    source = get_inheritance_source(file_path, sid, mask)
                else:
                    source = "Set Here"

                if (account, source) in encountered_principal_sources:

                    source = " "
                else:
                    # Add the (account, source) pair to the set
                    encountered_principal_sources.add((account, source))

                type_path_permission=check_inheritance_type(ace_flags)

                # Append to user-specific permission results
                user_permissions.append((account, permission, source, type_path_permission))

        return user_permissions

    except Exception as e:
        return [("Error", str(e), "")]

# List the permission for the provided folder path and group
def get_group_permissions_only(file_path):
    try:
        # Retrieve the security descriptor for the given file
        security_reader = win32security.GetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION)
        dacl = security_reader.GetSecurityDescriptorDacl()

        if dacl is None:
            return [("Error", "No DACL found", "")]

        group_permissions = []

        # Loop through all Access Control Entries (ACE)
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            ace_flags = ace[0][1]
            mask = ace[1]
            sid = ace[2]

            # Check only for "Group" principals
            principal_type = get_principal_type(sid)
            if principal_type == "Group":  # Only process Groups
                try:
                    # Retrieve DOMAIN\USERNAME from SID
                    user, domain, _ = win32security.LookupAccountSid(None, sid)
                    account = f"{domain}\\{user}"
                except win32security.error:
                    account = f"Unknown SID: {sid}"

                # Determine categorized permissions based on mask
                perms = determine_hierarch(mask)
                permission = "".join(perms)

                # Check for inheritance flags
                if ace_flags & win32security.INHERITED_ACE:
                    source = get_inheritance_source(file_path, sid, mask)
                else:
                    source = "Set Here"

                #Shows where the permissions are applied to
                type_path_permission=check_inheritance_type(ace_flags)

                # Append to user-specific permission results
                group_permissions.append((account, permission, source,type_path_permission))

        return group_permissions

    except Exception as e:
        return [("Error", str(e), "")]

# Decides if a user or a group
def get_principal_type(sid):
    try:
        _, _, account_type = win32security.LookupAccountSid(None, sid)
        if account_type == win32security.SidTypeUser:
            return "User"
        elif account_type == win32security.SidTypeGroup:
            return "Group"
        elif account_type == win32security.SidTypeWellKnownGroup:
            return "Well-Known Group"
        return "Other"
    except win32security.error:
        return "Unknown"


def get_all_folder_permission(root_path):
    """
    Retrieve permissions for all folders under a given root directory.

    This function traverses through all directories under the specified
    root path and retrieves their associated permissions. It constructs
    a relative path for each directory and maps it to its permissions
    in the returned dictionary. If an error occurs while processing a
    directory, the error will be printed and processing will continue
    with the next directory.

    :param root_path: The root directory path to start recursively gathering
        folder permissions.
    :return: A dictionary where each key is a relative path (as a string)
        of a folder under the root directory and the corresponding value
        is its permissions.
    """
    folder_permission = {}

    for dirpath, dirname, folder in os.walk(root_path, topdown=True):
        try:
            permissions = get_all_principal_permission(dirpath)
            relative_path = path.Path(dirpath).relative_to(root_path)
            folder_permission[str(relative_path)] = permissions

        except Exception as e:
            print(f"Error processing {dirpath}: {e}")

    return folder_permission

def store_all_principal_permission_as_dict(root_path):

    folder_permissions = {}

    # Traverse the tree
    for dirpath, principle, permission in os.walk(root_path, topdown=True):
        try:
            # Get permissions for the current folder
            permissions = get_all_principal_permission(dirpath)

            relative_path = path.Path(dirpath).relative_to(root_path)

            # Add permissions to the dictionary
            folder_permissions[str(relative_path)] = permissions

        except Exception as e:

            folder_permissions[str(path.Path(dirpath).relative_to(root_path))] = [
                ("Error", str(e), "None")
            ]

    return folder_permissions

def store_user_permissions_only_as_dict(root_path):
    folder_permissions = {}
    for dirpath, principle, permission in os.walk(root_path, topdown=True):
        try:
            permissions = get_user_permissions_only(dirpath)
            relative_path = path.Path(dirpath).relative_to(root_path)
            folder_permissions[str(relative_path)] = permissions
        except Exception as e:
            folder_permissions[str(path.Path(dirpath).relative_to(root_path))] = [
                ("Error", str(e), "None")
            ]
    return folder_permissions

def store_group_permissions_only_as_dict(root_path):
    folder_permissions = {}
    for dirpath, principle, permission in os.walk(root_path, topdown=True):
        try:
            permissions = get_group_permissions_only(dirpath)
            relative_path = path.Path(dirpath).relative_to(root_path)
            folder_permissions[str(relative_path)] = permissions
        except Exception as e:
            folder_permissions[str(path.Path(dirpath).relative_to(root_path))] = [
                ("Error", str(e), "None")
            ]
    return folder_permissions

def get_inheritance_source(file_path, sid, inherited_mask):
    parent_path = os.path.dirname(file_path)

    while parent_path:
        try:
            security_reader = get_cached_security_descriptor(parent_path)
            dacl = security_reader.GetSecurityDescriptorDacl()
            if dacl:
                for i in range(dacl.GetAceCount()):
                    ace = dacl.GetAce(i)
                    ace_flags = ace[0][1]
                    mask = ace[1]
                    sid = ace[2]

                    # Check if the current ACE matches the inherited SID and mask
                    if sid == sid and mask == inherited_mask and not ace_flags & win32security.INHERITED_ACE:
                        # If the permission is set here, return the source folder
                        return parent_path
        except Exception as e:
            print(f"Error while retrieving security for {parent_path}: {e}")
            return "Unknown"

        above_parent_path = os.path.dirname(parent_path)
        if above_parent_path == parent_path:
            break  # Reached the root directory
        parent_path = above_parent_path

    return "Unknown"

def check_inheritance_type(ace_flags):
    match ace_flags:
        case flags if flags & nt.OBJECT_INHERIT_ACE and flags & nt.CONTAINER_INHERIT_ACE:
            inheritance_type = "This Folder, Subfolders, and Files"
        case flags if flags & nt.OBJECT_INHERIT_ACE:
            inheritance_type = "This Folder and Files "
        case flags if flags & nt.CONTAINER_INHERIT_ACE:
            inheritance_type = "Subfolders Only"
        case _ if not ace_flags & (nt.OBJECT_INHERIT_ACE | nt.CONTAINER_INHERIT_ACE):
            inheritance_type = "This Folder Only"
    return inheritance_type

def preload_security_descriptors(root_path):
    security_descriptors = {}

    for dirpath, _, _ in os.walk(root_path):
        try:
            security_reader = win32security.GetFileSecurity(dirpath, win32security.DACL_SECURITY_INFORMATION)
            security_descriptors[dirpath] = security_reader
        except Exception as e:
            print(f"Error preloading security descriptor for {dirpath}: {e}")
            security_descriptors[dirpath] = None  # Mark as failed to retrieve

    return security_descriptors

def get_cached_security_descriptor(file_path):
    if file_path in security_descriptor_cache:
        return security_descriptor_cache[file_path]

    try:
        security_reader = win32security.GetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION)
        security_descriptor_cache[file_path] = security_reader
        return security_reader
    except Exception as e:
        print(f"Error retrieving security descriptor for {file_path}: {e}")
        return None


