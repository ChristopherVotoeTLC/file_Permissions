import os
import threading
from logging import exception
import ntsecuritycon as nt
import win32security
import pathlib as path
from concurrent.futures import ThreadPoolExecutor, as_completed


security_cache_lock = threading.Lock()
sid_cache_lock = threading.Lock()
user_permissions_tracker = {}


PERMISSION_HIERARCH ={
    "Full Control": nt.FILE_ALL_ACCESS,
    "Modify": (nt.FILE_GENERIC_EXECUTE| nt.FILE_DELETE_CHILD| nt.FILE_GENERIC_READ | nt.FILE_GENERIC_WRITE ),
    "Read & Execute": nt.FILE_GENERIC_READ | nt.FILE_GENERIC_EXECUTE,
    "Write": nt.FILE_GENERIC_WRITE,
    "Read": nt.FILE_GENERIC_READ,
}


security_descriptor_cache = {}
sid_cache_dict = {}


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
def get_all_principal_permission(root_path):
    try:
        print(f"Debug: Processing file: {root_path}")

        # Retrieve the security descriptor and DACL
        security_reader = win32security.GetFileSecurity(root_path, win32security.DACL_SECURITY_INFORMATION)
        dacl = security_reader.GetSecurityDescriptorDacl()

        if dacl is None:
            print(f"Debug: No DACL found for file: {root_path}")
            return [("Error", "No DACL found", "")]

        security_permissions = []
        encountered_principal_sources = set()

        # Loop through all ACEs
        print(f"Debug: Total ACEs for file: {root_path} = {dacl.GetAceCount()}")
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            ace_flags = ace[0][1]
            mask = ace[1]
            sid = ace[2]

            print(f"Debug: ACE #{i + 1} - SID: {sid}, Mask: {mask}, Flags: {ace_flags}")

            try:
                account = get_cached_sid(sid)
                print(f"Debug: Resolved SID to Account for ACE #{i + 1}: {account}")
            except Exception as e:
                print(f"Debug: Error resolving SID for ACE #{i + 1}: {sid}, Error: {e}")
                account = f"Unknown SID: {sid}"

            # Permission hierarchy
            perms = determine_hierarch(mask)
            source = "Set Here" if not (ace_flags & win32security.INHERITED_ACE) else get_inheritance_source(root_path,
                                                                                                             sid, mask)
            type_path_permission = check_inheritance_type(ace_flags)

            security_permissions.append((account, perms, source, type_path_permission))

        return security_permissions

    except Exception as ex:
        print(f"Debug: Error retrieving principal permissions for file: {root_path}, Error: {ex}")
        return [("Error", str(ex), "")]


# List the permission for the provided folder path and user
def get_user_permissions_only(root_path):
    try:
        # Retrieve the security descriptor for the given file
        security_reader = get_cached_security_descriptor(root_path)
        dacl = security_reader.GetSecurityDescriptorDacl()

        # Retrieve folder owner
        try:
            folder_owner = get_folder_owner(root_path)
        except exception as e:
            print(f"Error while retrieving owner for {root_path}: {e}")
            folder_owner = "Unknown"

        if dacl is None:
            return [("Error", "No DACL found", "")]

        user_permissions = []

        # Use a set to track (user_permission, inheritance_type) for GLOBAL tracking
        inherited_permissions_tracker = user_permissions_tracker.setdefault(root_path, set())

        # Loop through all Access Control Entries (ACE)
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            ace_flags = ace[0][1]
            mask = ace[1]  # permissions
            sid = ace[2]  # Security Identifier

            # Check only for "User" principals
            principal_type = get_principal_type(sid)

            if principal_type == "User":  #
                try:
                    account = get_cached_sid(sid)
                except win32security.error:
                    account = f"Unknown SID: {sid}"

                # Categorize the permission based on mask
                permission = determine_hierarch(mask)

                # Determine inheritance flags and type
                if ace_flags & win32security.INHERITED_ACE:
                    source = get_inheritance_source(root_path, sid, mask)
                else:
                    source = "Set Here"

                type_path_permission = check_inheritance_type(ace_flags)

                # Composite key for global tracking of user-permission-inheritance
                global_user_permission_key = (account, permission, type_path_permission)

                # Skip if permission is already inherited and unchanged
                if "This Folder, Subfolders, and Files" in type_path_permission:
                    if global_user_permission_key in inherited_permissions_tracker:
                        print(f"Skipping redundant permission for {account} in {root_path} - {permission}")
                        continue
                    else:
                        # Add to global tracker
                        inherited_permissions_tracker.add(global_user_permission_key)

                # Append the current result for local storage
                user_permissions.append((account, permission, source, type_path_permission, folder_owner))

        return user_permissions

    except Exception as e:
        return [("Error", str(e), "")]




# List the permission for the provided folder path and group
def get_group_permissions_only(root_path):
    try:
        # Retrieve the security descriptor for the given file
        security_reader = win32security.GetFileSecurity(root_path, win32security.DACL_SECURITY_INFORMATION)
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
                    account=get_cached_sid(sid)
                except win32security.error:
                    account = f"Unknown SID: {sid}"

                # Determine categorized permissions based on mask
                perms = determine_hierarch(mask)
                permission = "".join(perms)

                # Check for inheritance flags
                if ace_flags & win32security.INHERITED_ACE:
                    source = get_inheritance_source(root_path, sid, mask)
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

# def get_all_folder_permission(root_path):
#     """
#     Retrieve permissions for all folders under a given root directory.
#
#     This function traverses through all directories under the specified
#     root path and retrieves their associated permissions. It constructs
#     a relative path for each directory and maps it to its permissions
#     in the returned dictionary. If an error occurs while processing a
#     directory, the error will be printed and processing will continue
#     with the next directory.
#
#     :param root_path: The root directory path to start recursively gathering
#         folder permissions.
#     :return: A dictionary where each key is a relative path (as a string)
#         of a folder under the root directory and the corresponding value
#         is its permissions.
#     """
#     folder_permission = {}
#
#     for dirpath, dirname, folder in os.walk(root_path, topdown=True):
#         try:
#             permissions = get_all_principal_permission(dirpath)
#             relative_path = path.Path(dirpath).relative_to(root_path)
#             folder_permission[str(relative_path)] = permissions
#
#         except Exception as e:
#             print(f"Error processing {dirpath}: {e}")
#
#     return folder_permission

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

# def store_user_permissions_only_as_dict(root_path):
#     folder_permissions = {}
#     folder_count=0
#     for dirpath, principle, permission in os.walk(root_path, topdown=True):
#         try:
#             folder_count+=1
#             permissions = get_user_permissions_only(dirpath)
#             relative_path = path.Path(dirpath).relative_to(root_path)
#             folder_permissions[str(relative_path)] = permissions
#             print(f"{folder_count}")
#         except Exception as e:
#             folder_permissions[str(path.Path(dirpath).relative_to(root_path))] = [
#                 ("Error", str(e), "None")
#             ]
#     return folder_permissions

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
#List version, MID
# def get_cached_sid(sid):
#     try:
#         # Print the current cache size for debugging
#        # print(f"Debug: Current SID cache size: {len(sid_cache)}")
#
#         # Iterate through the list to find the SID
#         for cached_sid, cached_account in sid_cache:
#             if cached_sid == sid:
#                 #print(f"Debug: SID found in cache: {sid}")
#                 return cached_account
#
#
#         #print(f"Debug: Resolving SID: {sid}")
#         user, domain, _ = win32security.LookupAccountSid(None, sid)
#         account = f"{domain}\\{user}"
#         #print(f"Debug: Successfully resolved SID to Account: {account}")
#
#     except win32security.error as e:
#         #print(f"Debug: Win32 error resolving SID: {sid}, Error: {e}")
#         account = f"Unknown SID: {sid}"
#
#     except Exception as e:
#         #print(f"Debug: Unexpected error while resolving SID: {sid}, Error: {e}")
#         account = f"Unknown SID (Unknown Error)"
#
#     # Always cache the result to avoid reprocessing problematic entries
#     sid_cache.append((sid, account))
#     return account

def hash_sid(sid):

    sid_string = win32security.ConvertSidToStringSid(sid)
    return hash(sid_string)

# def get_cached_sid(sid):
#     try:
#         hashed_sid = hash_sid(sid)
#
#         with sid_lock:
#             if hashed_sid in sid_cache_dict:
#                 return sid_cache_dict[hashed_sid]
#
#         user, domain, _ = win32security.LookupAccountSid(None, sid)
#         account = f"{domain}\\{user}"
#
#         with threading.Lock():
#             sid_cache_dict[hashed_sid] = account
#         return account
#     except Exception as e:
#         return f"Unknown SID (Error: {e})"

# def get_cached_security_descriptor(file_path):
#
#     with security_cache_lock:
#         if file_path in security_descriptor_cache:
#             return security_descriptor_cache[file_path]
#
#     try:
#         security_reader = win32security.GetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION)
#
#         with security_cache_lock:
#             security_descriptor_cache[file_path] = security_reader
#
#         return security_reader
#     except Exception as e:
#         print(f"Error retrieving security descriptor for {file_path}: {e}")
#         return None

def get_folder_owner(file_path):
    try:

        if os.path.dirname(file_path) == file_path:
            root_path = os.path.splitdrive(file_path)[0] + "\\"
            file_path = root_path

        # Use win32security to get the owner descriptor
        security_descriptor = win32security.GetFileSecurity(
            file_path, win32security.OWNER_SECURITY_INFORMATION
        )
        owner_sid = security_descriptor.GetSecurityDescriptorOwner()
        owner_name, domain, _ = win32security.LookupAccountSid(None, owner_sid)

        owner = f"{domain}\\{owner_name}"
        print(f"Retrieved Owner for {file_path}: {owner}")
        return owner

    except Exception as e:
        return f"Error retrieving owner: {e}"


#Multithread ????
def process_folder_permissions(folder_path, root_path, cache, cache_lock):
    try:
        # Retrieve user permissions for the current folder
        folder_permissions = get_user_permissions_only(folder_path)
        relative_path = path.Path(folder_path).relative_to(root_path)

        #
        with cache_lock:
            cache[str(relative_path)] = folder_permissions

    except Exception as e:
        with cache_lock:
            cache[str(path.Path(folder_path).relative_to(root_path))] = [
                ("Error", str(e), "None")
            ]

def store_user_permissions_only_as_dict_multithreaded(root_path, max_workers=8):

    folder_permissions = {}
    cache_lock = threading.Lock()  # To ensure thread-safe cache access


    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        tasks = [
            executor.submit(process_folder_permissions, dirpath, root_path, folder_permissions, cache_lock)
            for dirpath, _, _ in os.walk(root_path, topdown=False)
        ]


        for future in as_completed(tasks):
            try:
                future.result()
            except Exception as exc:
                print(f"Error processing task: {exc}")

    return folder_permissions
#____________________________________________________________________________________

def get_cached_security_descriptor(file_path):

    with security_cache_lock:
        if file_path in security_descriptor_cache:

            #print(f"[Cache Hit: Security Descriptor] {file_path}")
            return security_descriptor_cache[file_path]

    try:
        security_reader = win32security.GetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION)

        with security_cache_lock:
            security_descriptor_cache[file_path] = security_reader

            #print(f"[Cache Miss: Security Descriptor] {file_path}")

        return security_reader
    except Exception as e:
        print(f"Error retrieving security descriptor for {file_path}: {e}")
        return None

def get_cached_sid(sid):

    try:
        hashed_sid = hash_sid(sid)

        with sid_cache_lock:
            if hashed_sid in sid_cache_dict:
                return sid_cache_dict[hashed_sid]

        user, domain, _ = win32security.LookupAccountSid(None, sid)
        account = f"{domain}\\{user}"

        with sid_cache_lock:
            sid_cache_dict[hashed_sid] = account

        return account
    except Exception as e:
        return f"Unknown SID (Error: {e})"