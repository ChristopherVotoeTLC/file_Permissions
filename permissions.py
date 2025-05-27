import os
import ntsecuritycon as nt
import win32security
import pathlib as path
import datetime
import time



PERMISSION_HIERARCH ={
    "Full Control": nt.FILE_ALL_ACCESS,
    "Modify": (nt.FILE_GENERIC_EXECUTE| nt.FILE_DELETE_CHILD| nt.FILE_GENERIC_READ | nt.FILE_GENERIC_WRITE ),
    "Read & Execute": nt.FILE_GENERIC_READ | nt.FILE_GENERIC_EXECUTE,
    "Write": nt.FILE_GENERIC_WRITE,
    "Read": nt.FILE_GENERIC_READ,
}


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
                source = "Inherited from above"
            else:
                source = "None"

            security_permission.append((account, permission, source))

        return security_permission

    except Exception as e:
        return [("Error", str(e), "")]

# List the permission for the provided folder path and user
def get_user_permissions_only(file_path):
    try:
        # Retrieve the security descriptor for the given file
        security_reader = win32security.GetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION)
        dacl = security_reader.GetSecurityDescriptorDacl()

        if dacl is None:
            return [("Error", "No DACL found", "")]

        user_permissions = []

        # Loop through all Access Control Entries (ACE)
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            ace_flags = ace[0][1]
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
                    source = "Inherited from above"
                else:
                    source = "None"

                # Append to user-specific permission results
                user_permissions.append((account, permission, source))

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
                    source = "Inherited from above"
                else:
                    source = "None"

                # Append to user-specific permission results
                group_permissions.append((account, permission, source))

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

# Prints name, permission and inheritance
def print_all_principal_permission(root_path, progress_callback=None):
    start = time.time()
    folder_permission_data = get_all_folder_permission(root_path)

    # Allows me to save the report to their downloads with a timestamp
    try:
        downloads_dir = os.path.join(os.getenv("USERPROFILE") or os.getenv("HOME"), "Downloads")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_filename = os.path.join(downloads_dir, f"permissions_report_{timestamp}.txt")
    except Exception as e:
        print(f"Error: {e}")

    num_folders = len(folder_permission_data)
    if progress_callback:
        progress_callback(0, num_folders)
    i = 0
    # if not self.inheritance_checkbox.isChecked():
    with open(report_filename, 'w') as f:
        f.write(f"Below are all permission for all folders in: {root_path}\n")
        f.write("-" * 173 + "\n")

        root_permissions = get_all_principal_permission(root_path)
        f.write(f"\nRoot Folder: {root_path}\n")
        f.write("-" * 173 + "\n")
        f.write(f"{'User/Group':40} {'Permission':25} {'Source'}\n")
        f.write("-" * 173 + "\n")

        try:
            for user, perm, src in root_permissions:
                i += 1
                f.write(f"{user:40} {perm:25} {src}\n")
            f.write("-" * 173 + "\n")
            for folder_path, permissions in folder_permission_data.items():

                f.write(f"\nSubfolder: {root_path}\\{folder_path}\n")
                f.write("-" * 173 + "\n")
                f.write(f"{'User/Group':40} {'Permission':25} {'Source'}\n")
                f.write("-" * 173 + "\n")

                for user, perm, src in permissions:
                    f.write(f"{user:40} {perm:25} {src}\n")
                f.write("-" * 173 + "\n")
        except Exception as e:
            print(f"An error occurred: {e}")
    # else:
    # print("This is the inheritance report")
    # Future inheritance method

    if progress_callback:
        progress_callback(i, num_folders)

    end = time.time()
    total_time = end - start
    print(f"Results have been written to {report_filename}")

    # Opens the file after saving
    try:
        os.startfile(report_filename)
    except Exception as e:
        print(f"Error: {e}")

    return total_time, report_filename

# print name, permission, and inheritance for users principal only
def print_all_user_permission(root_path, progress_callback=None):
    start = time.time()

    folder_permission_data = {}

    try:
        # Walk through all folders and subfolders
        for dirpath, _, _ in os.walk(root_path):
            permissions = get_user_permissions_only(dirpath)
            folder_permission_data[os.path.relpath(dirpath, root_path)] = permissions

    except Exception as e:
        print(f"Error while gathering permissions: {e}")
        return None

    # Save the report to the Downloads folder
    try:
        downloads_dir = os.path.join(os.getenv("USERPROFILE") or os.getenv("HOME"), "Downloads")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_filename = os.path.join(downloads_dir, f"permissions_report_users_{timestamp}.txt")
    except Exception as e:
        print(f"Error: {e}")
        return None

    num_folders = len(folder_permission_data)
    if progress_callback:
        progress_callback(0, num_folders)

    i = 0
    # Write the report to a file
    with open(report_filename, 'w') as f:
        f.write(f"Below are all user-specific permissions for all folders in: {root_path}\n")
        f.write("-" * 173 + "\n")

        root_permissions = get_user_permissions_only(root_path)
        f.write(f"\nRoot Folder: {root_path}\n")
        f.write("-" * 173 + "\n")
        f.write(f"{'User':40} {'Permission':25} {'Source'}\n")
        f.write("-" * 173 + "\n")

        try:
            for user, perm, src in root_permissions:
                i += 1
                f.write(f"{user:40} {perm:25} {src}\n")
            f.write("-" * 173 + "\n")

            for folder_path, permissions in folder_permission_data.items():
                f.write(f"\nSubfolder: {root_path}\\{folder_path}\n")
                f.write("-" * 173 + "\n")
                f.write(f"{'User':40} {'Permission':25} {'Source'}\n")
                f.write("-" * 173 + "\n")

                for user, perm, src in permissions:
                    i += 1
                    f.write(f"{user:40} {perm:25} {src}\n")
                f.write("-" * 173 + "\n")

        except Exception as e:
            print(f"An error occurred while writing to the report: {e}")

    if progress_callback:
        progress_callback(i, num_folders)

    end = time.time()
    total_time = end - start
    print(f"Results have been written to {report_filename}")

    # Open the report file
    try:
        os.startfile(report_filename)
    except Exception as e:
        print(f"Error opening the report: {e}")

    return total_time, report_filename

# print name, permission, and inheritance for group principal only
def print_all_groups_permission(root_path, progress_callback=None):
    start = time.time()

    folder_permission_data = {}

    try:
        # Walk through all folders and subfolders
        for dirpath, _, _ in os.walk(root_path):
            permissions = get_group_permissions_only(dirpath)
            folder_permission_data[os.path.relpath(dirpath, root_path)] = permissions

    except Exception as e:
        print(f"Error while gathering permissions: {e}")
        return None

    # Save the report to the Downloads folder
    try:
        downloads_dir = os.path.join(os.getenv("USERPROFILE") or os.getenv("HOME"), "Downloads")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_filename = os.path.join(downloads_dir, f"permissions_report_users_{timestamp}.txt")
    except Exception as e:
        print(f"Error: {e}")
        return None

    num_folders = len(folder_permission_data)
    if progress_callback:
        progress_callback(0, num_folders)

    i = 0
    # Write the report to a file
    with open(report_filename, 'w') as f:
        f.write(f"Below are all group-specific permissions for all folders in: {root_path}\n")
        f.write("-" * 173 + "\n")

        root_permissions = get_group_permissions_only(root_path)
        f.write(f"\nRoot Folder: {root_path}\n")
        f.write("-" * 173 + "\n")
        f.write(f"{'Group':40} {'Permission':25} {'Source'}\n")
        f.write("-" * 173 + "\n")

        try:
            for group, perm, src in root_permissions:
                i += 1
                f.write(f"{group:40} {perm:25} {src}\n")
            f.write("-" * 173 + "\n")

            for folder_path, permissions in folder_permission_data.items():
                f.write(f"\nSubfolder: {root_path}\\{folder_path}\n")
                f.write("-" * 173 + "\n")
                f.write(f"{'Group':40} {'Permission':25} {'Source'}\n")
                f.write("-" * 173 + "\n")

                for group, perm, src in permissions:
                    i += 1
                    f.write(f"{group:40} {perm:25} {src}\n")
                f.write("-" * 173 + "\n")

        except Exception as e:
            print(f"An error occurred while writing to the report: {e}")

    if progress_callback:
        progress_callback(i, num_folders)

    end = time.time()
    total_time = end - start
    print(f"Results have been written to {report_filename}")

    # Open the report file
    try:
        os.startfile(report_filename)
    except Exception as e:
        print(f"Error opening the report: {e}")

    return total_time, report_filename

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

