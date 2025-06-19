import re
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QListWidget, QProgressBar, QFileDialog,
    QLineEdit, QShortcut, QPushButton, QCheckBox, QApplication, QHBoxLayout, QTreeWidget, QTreeWidgetItem
)
import qtawesome as qta
import os
from permissions import (
    store_all_permissions_only_as_dict_multithreaded, store_user_permissions_only_as_dict_multithreaded,
    store_group_permissions_only_as_dict_multithreaded
)
from Database.database import (
query_job_info,query_folder_content_info,query_permissions_info
)

class TestGUI(QMainWindow):


    def __init__(self):
        super().__init__()
        self.start_gui()

    def start_gui(self):
        # Set up a window
        self.setWindowTitle("Folder Permissions GUI")
        # Adds the fullscreen/minimize/close in the top right of the gui
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.setGeometry(20,26, 1800, 1000)

        # Styling!!
        self.setStyleSheet("""
    /* Main Window */
    QMainWindow {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: #000000;  /* text color */
        font-family: "Roboto", sans-serif; /* not sure which this affects yet*/
        font-size: 18px;
    }

    /* Labels for headings*/
    QLabel {
        color: #000000;
        font-size: 18px;
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        padding: 5px;
    }

    /* Input fields (QLineEdit) */
    QLineEdit {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: #00000; /*TEXT COLOR*/
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size : 15px;
        border: 1px solid #2c3e50;
        border-radius: 8px;
        padding: 5px;
    }
    QLineEdit:focus {
        border: 1px solid #3498db;  /* Focus color */
    }

    /* Buttons (QPushButton) */
    QPushButton {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: black;
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size : 15px;
        border: 1px solid #2c3e50;
        border-radius: 10px;
        padding: 7px 15px;

    }
    QPushButton:hover {
        background-color: #2980b9;  /* Hover effect */
    }
    QPushButton:pressed {
        background-color: #1c598b;  /* Pressed effect */
    }

    /*Checkbox*/
    QCheckBox {
    font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size : 15px;
    }

    /* Progress Bar */
    QProgressBar {
        text-align: center;
        color: black; /*text*/
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        border: 1px solid #2c3e50;
        border-radius: 5px;
    }
    QProgressBar::chunk {
        background-color: #39c45f;  /* Fill color */
        border-radius: 5px;
    }

    /* List Widget */
    QListWidget {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: #000000; /*Input field text color*/
        border: 1px solid #2c3e50;
        border-radius: 5px;
        padding: 5px;
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size: 15px; /*affects text in list*/
    }
    QListWidget::item {
        padding: 5px;
        border: none;
    }
    QListWidget::item:hover {

    }
    QListWidget::item:selected {

        color: black;
    }

    /* QFileDialog (Browse File Dialog) */
    QFileDialog {
        background-color: #2c3e50;
        color: white;
    }

    QTreeWidget {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: #000000; /*Input field text color*/
        padding: 5px;
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size: 12px; 
    }
    /*Children branches such as each folder*/
    QTreeWidget::item:!has-children { 

        color: #00000;
        font-weight: Normal;
        font-family: "Roboto", sans-serif;
        font-size: 12px; 

    }

    QHeaderView {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: #000000; /*Input field text color*/
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size: 15px; 
    }
    QHeaderView::section {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        border: 1px solid #4ca1af;  
        padding: 2px;

    }
    QScrollBar:vertical {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        border: none;
    }
""")

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Allows items on the same line
        self.horizontal_layout = QHBoxLayout()
        layout.addLayout(self.horizontal_layout)

        # Folder Path Input
        folder_path_label = QLabel("Choose Project Year Folder:")
        self.horizontal_layout.addWidget(folder_path_label)



        # Input line with a file path
        self.file_path_input = QLineEdit()
        self.horizontal_layout.addWidget(self.file_path_input)
        # _2077_button = QPushButton("2077")
        # #_2020_button.setIcon(qta.icon('fa5s.search'))
        # _2077_button.clicked.connect(lambda: self.handle_submit("2077"))
        # self.horizontal_layout.addWidget(_2077_button)
        #
        #
        # _2021_button = QPushButton("2021")
        # #_2021_button.setIcon(qta.icon('fa5s.search'))
        # _2021_button.clicked.connect(lambda: self.handle_submit("2021"))
        # self.horizontal_layout.addWidget(_2021_button)
        #
        # _2022_button = QPushButton("2022")
        # #_2022_button.setIcon(qta.icon('fa5s.search'))
        # _2022_button.clicked.connect(lambda: self.handle_submit("2022"))
        # self.horizontal_layout.addWidget(_2022_button)
        #
        # _2023_button = QPushButton("2023")
        # #_2023_button.setIcon(qta.icon('fa5s.search'))
        # _2023_button.clicked.connect(lambda: self.handle_submit("2023"))
        # self.horizontal_layout.addWidget(_2023_button)
        #
        # _2024_button = QPushButton("2024")
        # #_2024_button.setIcon(qta.icon('fa5s.search'))
        # _2024_button.clicked.connect(lambda: self.handle_submit("2024"))
        # self.horizontal_layout.addWidget(_2024_button)
        #
        # _2025_button = QPushButton("2025")
        # #_2025_button.setIcon(qta.icon('fa5s.search'))
        # _2025_button.clicked.connect(lambda: self.handle_submit("2025"))
        # self.horizontal_layout.addWidget(_2025_button)

        # self.display_all_perms = QCheckBox("Display All Permissions (Will take longer to compute)")
        # self.display_all_perms.setChecked(False)
        # self.display_all_perms.stateChanged.connect(self.toggle_display_all_permissions)
        # layout.addWidget(self.display_all_perms)



        # Browse Button
        browse_button = QPushButton("Browse")
        browse_button.setIcon(qta.icon('fa5s.file-import'))
        browse_button.clicked.connect(self.browse_folder)
        self.horizontal_layout.addWidget(browse_button)

        # Submit Button and Progress Bar Layout
        submit_button = QPushButton("Search")
        submit_button.setIcon(qta.icon('fa5s.search'))
        submit_button.clicked.connect(self.handle_submit)
        self.horizontal_layout.addWidget(submit_button)

        # Inheritance Checkbox
        # self.inheritance_checkbox = QCheckBox("Include Inherited Permissions (Will take longer to compute)")
        # self.inheritance_checkbox.setChecked(False)
        # layout.addWidget(self.inheritance_checkbox)

        # self.show_groups_checkbox = QCheckBox("Include Groups")
        # self.show_groups_checkbox.setChecked(False)
        # layout.addWidget( self.show_groups_checkbox)

        # self.show_users_checkbox = QCheckBox("Only Users")
        # self.show_users_checkbox.setChecked(True)
        # layout.addWidget(self.show_users_checkbox)

        # Project Details Sections
        # project_details_label = QLabel("Project Details: (Ctrl + A to select all & Ctrl + C to copy)")
        # layout.addWidget(project_details_label)
        #
        # self.project_info_list = QListWidget()
        # self.project_info_list.setSelectionMode(QListWidget.ExtendedSelection)
        # layout.addWidget(self.project_info_list)
        #
        # # Enable copy and select-all shortcuts
        # copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        # copy_shortcut.activated.connect(self.copy_selected_items)
        #
        # select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        # select_all_shortcut.activated.connect(self.select_all_items)

        # Tree widget for displaying folder structure and permissions
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Folder","Folder Owner", "Principle","Permission","Inheritance Source","Inheritance Type"])

        self.inherited_permissions = {}

        self.tree_widget.setColumnWidth(0, 350)
        self.tree_widget.setColumnWidth(1, 200)
        self.tree_widget.setColumnWidth(2, 275)
        self.tree_widget.setColumnWidth(3, 200)
        self.tree_widget.setColumnWidth(4, 450)
        self.tree_widget.setColumnWidth(5, 250)
        layout.addWidget(self.tree_widget)

        self.tree_widget.itemExpanded.connect(self.on_tree_expand)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)

        # # Add a test item with a placeholder "Loading..." child
        # test_item = QTreeWidgetItem(["Sample Job", "Owner", "", "", "", ""])
        # test_item.setData(0, Qt.UserRole, {"type": "job", "id": 1})  # Example metadata
        # test_item.addChild(QTreeWidgetItem(["Loading..."]))
        # self.tree_widget.addTopLevelItem(test_item)
        #
        # folder_item = QTreeWidgetItem(["Sample Folder", "Owner", "", "", "", ""])
        # folder_item.setData(0, Qt.UserRole, {"type": "folder", "path": "/path/to/folder"})
        # folder_item.addChild(QTreeWidgetItem(["Loading..."]))
        # test_item.addChild(folder_item)

        search_layout = QHBoxLayout()

        # Search Tree input
        self.search_tree = QLineEdit()
        self.search_tree.setPlaceholderText("Enter search term...")
        search_layout.addWidget(self.search_tree)

        # Search button
        search_button = QPushButton("Search")
        search_button.setIcon(qta.icon('fa5s.search'))

        search_button.clicked.connect(self.search_tree_1)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        # -----------------------------Got rid of to use only tree widget------------------------#
        # Label with file location
        # self.file_location_label = QLabel("File Location:")
        # layout.addWidget(self.file_location_label)
        # self.file_path = QLineEdit()
        # layout.addWidget(self.file_path)
        # --------------------------------------------------------------------------------------

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

    # def update_tree_widget(self, folder_permissions):
    #     self.tree_widget.clear()
    #
    #     # Dict to store which folders become children of other folders in the tree
    #     tree_data = {}
    #
    #     # Build the tree_data dictionary
    #     for folder, permissions in folder_permissions.items():
    #         parts = folder.split("\\")  # splits folder_path
    #         first_part = parts[0]  # This is the top branch
    #
    #         # If it doesn't exist in tree_data, add it
    #         if first_part not in tree_data:
    #             tree_data[first_part] = {"permissions": [], "subfolders": {}}
    #             # Permission holds rules while subfolder hold child branches
    #
    #         current_level = tree_data[first_part]
    #         for part in parts[1:]:
    #             if part not in current_level["subfolders"]:
    #                 current_level["subfolders"][part] = {"permissions": [], "subfolders": {}}
    #
    #             # moves to branch with subfolder and inserts it
    #             current_level = current_level["subfolders"][part]
    #
    #         # Once all subfolders are done, add the permissions
    #         current_level["permissions"].extend(permissions)
    #
    #     def add_items(parent_item, folder_data):
    #         # List that will hold all the branches, starts with just the parent branch and its data
    #         holder_list = [(parent_item, folder_data)]
    #
    #         while holder_list:
    #             current_parent, current_data = holder_list.pop()
    #
    #             # Iterate through folders at the current branch
    #             for folder_name, folder_details in current_data.items():
    #                 if folder_name == "permissions":
    #                     continue
    #
    #                 # Extract owner for this branch
    #                 branch_owner = folder_details["permissions"][0][4] if folder_details["permissions"] else "No Owner"
    #                 # 2025 folder with jobs starting in 225*** gave no owner but had owner?? test on 2024 folder
    #
    #                 # Create a new tree branch and display the owner once on this branch
    #                 folder_item = QTreeWidgetItem([folder_name, "", "", "", "", f"{branch_owner}"])
    #
    #                 current_parent.addChild(folder_item)
    #
    #                 # Add permissions for this branch
    #                 for user1, perm1, source1, type1, _ in folder_details["permissions"]:
    #                     permission_item1 = QTreeWidgetItem(
    #                         ["", f"{user1}", f"     {perm1}", f"{source1}", f"{type1}", ""]
    #                     )
    #                     folder_item.addChild(permission_item1)
    #
    #                 # Adds the branch to the hold list if the folder has subfolders
    #                 holder_list.append((folder_item, folder_details["subfolders"]))
    #
    #     # Starts filling the tree widget
    #     for top_folder, details, in tree_data.items():
    #         # Extract the owner of the top-level folder
    #         top_owner = details["permissions"][0][4] if details["permissions"] else "No Owner"
    #
    #         #
    #         top_item = QTreeWidgetItem([top_folder, "", "", "", "", top_owner])
    #         self.tree_widget.addTopLevelItem(top_item)
    #
    #         # Add permissions for the top-level
    #         for user, perm, source, type, _ in details["permissions"]:
    #             permission_item = QTreeWidgetItem(
    #                 ["", f"{user}", f"     {perm}", f"{source}", f"{type}", ""]
    #             )
    #             top_item.addChild(permission_item)
    #
    #         # Add subfolders
    #         add_items(top_item, details["subfolders"])
    #
    #     self.progress_bar.setValue(100)

    def search_tree_1(self):
        search_term = self.search_tree.text().strip()
        if not search_term:
            self.show_error_message("Please enter a search term.")
            return

        search_term = search_term.lower()

        self.highlight_searched_item(self.tree_widget, search_term)

    def highlight_searched_item(self, tree_widget, search_term):

        for i in range(tree_widget.topLevelItemCount()):
            top_item = tree_widget.topLevelItem(i)
            self.search_items(top_item, search_term)

    def search_items(self, item, search_term):
        # Reset item background color by default
        item.setBackground(0, Qt.transparent)
        item.setBackground(1, Qt.transparent)
        item.setBackground(2, Qt.transparent)

        found = False


        # Check if any column text contains the search term
        for col in range(item.columnCount()):
            if search_term in item.text(col).lower():
                # Highlight the matching item
                item.setBackground(col, Qt.yellow)
                found = True
        if found:
            self.tree_widget.scrollToItem(item)

        for i in range(item.childCount()):
            child = item.child(i)
            self.search_items(child, search_term)

    def clear_tree_selection(self):
        # Iterate over all top-level items
        for i in range(self.tree_widget.topLevelItemCount()):
            top_item = self.tree_widget.topLevelItem(i)
            self.clear_items(top_item)

    def clear_items(self, item):
        # Reset background color for each column
        for col in range(item.columnCount()):
            item.setBackground(col, Qt.transparent)

        # Recursively clear background color for all children
        for i in range(item.childCount()):
            child = item.child(i)
            self.clear_items(child)

    # Used to open a folder directory when browse is clicked
    def browse_folder(self):
        selected_folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if selected_folder:
            self.file_path_input.setText(selected_folder)

    def handle_submit(self):

        try:
            file_path = self.file_path_input.text().strip()
            pattern = r"L:/\d{4}-Jobs.*"
            if re.fullmatch(pattern, file_path):
                year = file_path.split("/")[1][:4]
                print(f"Year received: {year}")
                job_info = query_job_info(year)

                # Clear the tree and populate jobs
                self.tree_widget.clear()
                self.populate_jobs(job_info)
            else:
                print("Year not found or file path is invalid.")

        except Exception as e:
                print(f"Error in handle_submit: {e}")

    def on_tree_expand(self, item):
        try:

            if item.childCount() == 1 and item.child(0).text(0) == "Loading...":
                item.takeChildren()


                node_info = item.data(0, Qt.UserRole)
                if not node_info or "type" not in node_info:
                    print(f"Invalid metadata for the expanded item: {item.text(0)}")
                    return


                if node_info["type"] == "job":
                    try:

                        folders = query_folder_content_info(node_info["id"])

                        # Create a mapping of parent IDs to their children
                        folder_map = {}
                        for folder_id, parent_folder, folder_owner, folder_path in folders:
                            folder_map.setdefault(parent_folder, []).append(
                                (folder_id, folder_owner, folder_path)
                            )

                        # Builds folder tree
                        self.add_subfolders(item, None, folder_map)

                    except Exception as e:
                        print(f"Error loading folders for job {node_info['id']}: {e}")

                # For "folder" type, fetch permissions lazily (only when the folder is clicked/expanded)
                elif node_info["type"] == "folder":
                    try:
                        # Fetch permissions for this folder
                        permissions = query_permissions_info(node_info["id"])
                        print(f"Permissions for folder {node_info['path']}: {permissions}")

                        # Add permissions as children of this folder
                        for principal, perm, inh_type, inh_source in permissions:
                            # Add permission as a child
                            perm_item = QTreeWidgetItem(["", "", principal, perm, inh_type, inh_source])
                            item.addChild(perm_item)

                    except Exception as e:
                        print(f"Error loading permissions for folder {node_info['id']}: {e}")

                # Mark the node as loaded
                node_info["loaded"] = True
                item.setData(0, Qt.UserRole, node_info)

        except Exception as e:
            print(f"Error during tree expansion: {e}")

    def on_tree_item_clicked(self, item, column):

        try:
            if hasattr(self,"previous_item") and self.previous_item ==item:
                print(f"Item '{item.text(0)} is active, skipping")
                self.reset_tree(item)
                self.previous_item=None
                return

            # if hasattr(self, "previous_item") and self.previous_item is not None:
            #     #self.reset_tree(self.previous_item)
            #     print("test")

            self.progress_bar.setValue(13)

            node_info = item.data(0, Qt.UserRole)
            if not node_info or "type" not in node_info:
                print(f"Invalid metadata for the clicked item: {item.text(0)}")
                return

            # Check if the clicked item is a folder
            if node_info["type"] == "folder":


                if node_info.get("loaded", False):
                    print(f"Permissions for folder '{item.text(0)}' are already loaded.")
                    self.reset_tree(item)
                    self.progress_bar.setValue(0)
                    return


                permissions = query_permissions_info(node_info["id"])
                print(f"Permissions fetched for folder '{item.text(0)}': {permissions}")


                parent_folder_id = node_info.get("parent_folder")
                parent_permissions = self.inherited_permissions.get(parent_folder_id, set())

                # Filter out inherited permissions
                unique_permissions = []
                current_permissions = set()
                for principal, perm, source, inh_type in permissions:
                    # Check if the principal and permission are not already inherited
                    if (principal, perm) not in parent_permissions:
                        unique_permissions.append((principal, perm, source, inh_type))
                        current_permissions.add((principal, perm))


                if unique_permissions:
                    principals = "\n".join([perm[0] for perm in unique_permissions])
                    perms = "\n".join([perm[1] for perm in unique_permissions])
                    inh_types = "\n".join([perm[3] for perm in unique_permissions])
                    sources = "\n".join([perm[2] for perm in unique_permissions])

                    # Update the tree item with unique permissions
                    item.setText(2, principals)
                    item.setText(3, perms)
                    item.setText(4, inh_types)
                    item.setText(5, sources)
                else:
                    # If no unique permissions exist, indicate this
                    item.setText(3, "All Permissions Inherited")

                # Update inherited permissions for the current folder
                self.inherited_permissions[node_info["id"]] = current_permissions


                node_info["loaded"] = True
                item.setData(0, Qt.UserRole, node_info)
                self.progress_bar.setValue(100)

            self.previous_item = item

        except Exception as e:
            print(f"Error handling item click: {e}")
    def reset_tree(self,item):
        try:
            node_info = item.data(0, Qt.UserRole)
            if not node_info or "type" not in node_info:
                return

            # Reset only if the item is a folder
            if node_info["type"] == "folder":
                # Clear the permission columns
                item.setText(2, "")
                item.setText(3, "")
                item.setText(4, "")
                item.setText(5, "")

                # Mark the node as not loaded (if needed for reloading)
                node_info["loaded"] = False
                item.setData(0, Qt.UserRole, node_info)
                self.progress_bar.setValue(0)

        except Exception as e:
            print(f"Error resetting tree item: {e}")

    def add_subfolders(self, parent_item, parent_id, folder_map):

        for folder_id, folder_owner, folder_path in folder_map.get(parent_id, []):

            relative_path = os.path.basename(folder_path)

            # Create a tree item for this folder
            folder_item = QTreeWidgetItem([relative_path, folder_owner, "", "", "", ""])
            folder_item.setData(0, Qt.UserRole,
                                {"type": "folder", "id": folder_id, "path": folder_path, "parent_folder": parent_id,
                                 "loaded": False})


            # Add this folder to the parent item
            parent_item.addChild(folder_item)

            #
            self.add_subfolders(folder_item, folder_id, folder_map)

    def populate_jobs(self, job_info):
        try:
            for job_id,job_info in job_info:

                job_branch = QTreeWidgetItem([job_info, "", "", "", "", ""])
                job_branch.setData(0, Qt.UserRole, {"type": "job", "id": job_id})
                job_branch.addChild(QTreeWidgetItem(["Loading..."]))
                self.tree_widget.addTopLevelItem(job_branch)

            # # Build a dictionary to represent the folder hierarchy for this job.
                # folder_hierarchy = {}
                # for folder_content_id, folder_owner, folder_path in folder_content_info:
                #     # Only add folders that belong to the current job.
                #     if not folder_path.startswith(job):
                #         continue
                #
                #     # Normalize the folder path relative to the job folder.
                #     relative_path = folder_path[len(job):].strip("\\")
                #     parts = relative_path.split("\\") if relative_path else []
                #
                #     # Build the nested hierarchy.
                #     current_level = folder_hierarchy
                #     for part in parts:
                #         if part not in current_level:
                #             current_level[part] = {
                #                 "owner": folder_owner,
                #                 "id": folder_content_id,
                #                 "subfolders": {}
                #             }
                #         # Move deeper in the hierarchy.
                #         current_level = current_level[part]["subfolders"]
                #
                # # Recursive function to add a folder hierarchy and its permissions to the tree.
                # def add_subtree(parent_item, subtree, permissions_info):
                #     for folder_name, folder_data in subtree.items():
                #         folder_owner = folder_data["owner"]
                #         folder_content_id = folder_data["id"]
                #
                #         # Create a tree item for the current folder.
                #         folder_item = QTreeWidgetItem([folder_name, folder_owner, "", "", "", ""])
                #         parent_item.addChild(folder_item)
                #
                #         # Add permissions to the current folder.
                #         for perm_folder_content_id, principal, perm_type, inheritance_type, source in permissions_info:
                #             if perm_folder_content_id == folder_content_id:
                #                 permission_item = QTreeWidgetItem([
                #                     "", "", principal, perm_type, inheritance_type, source
                #                 ])
                #                 folder_item.addChild(permission_item)
                #
                #         # Recursively add subfolders.
                #         add_subtree(folder_item, folder_data["subfolders"], permissions_info)
                #
                # # Add the folder hierarchy for this job into the tree.
                # add_subtree(job_branch, folder_hierarchy, permissions_info)

        except Exception as e:
            print(f"Error in populate_jobs: {e}")

    def update_progress_bar(self, value):

        self.progress_bar.setValue(value)

    # def toggle_display_all_permissions(self, state):
    #
    #     if state == Qt.Checked:
    #         print("Display All Permissions is ON: Pre-loading all permissions.")
    #         self.load_all_permissions()
    #     else:
    #         print("Display All Permissions is OFF: Using lazy loading.")
    #         self.clear_tree_permissions()  # Optionally clear permissions if needed
    #
    # def load_all_permissions(self):
    #
    #     for i in range(self.tree_widget.topLevelItemCount()):
    #         top_item = self.tree_widget.topLevelItem(i)
    #         print(f"{top_item}")
    #         self.fetch_permissions_recursively(top_item)
    #
    # def fetch_permissions_recursively(self, item):
    #
    #     try:
    #         # Print info about the current node being processed
    #         print(f"Processing item: {item.text(0)}")
    #
    #         node_info = item.data(0, Qt.UserRole)
    #
    #         # Check if the item is of type 'folder'
    #         if node_info and node_info.get("type") == "job":
    #             print(f"Fetching permissions for folder: {item.text(0)}")
    #
    #             # Check if permissions are already loaded
    #             if node_info.get("loaded", False):
    #                 print(f"Permissions already loaded for folder: {item.text(0)}")
    #             else:
    #                 # Fetch permissions for the folder
    #                 permissions = query_permissions_info(node_info["id"])
    #                 print(f"Fetched permissions for folder '{item.text(0)}': {permissions}")
    #
    #                 # Add permissions as children of this folder
    #                 for principal, perm, inh_type, inh_source in permissions:
    #                     perm_item = QTreeWidgetItem(["", "", principal, perm, inh_type, inh_source])
    #                     item.addChild(perm_item)
    #
    #                 # Mark the folder as loaded
    #                 node_info["loaded"] = True
    #                 item.setData(0, Qt.UserRole, node_info)
    #
    #         # Recursively process all children
    #         for i in range(item.childCount()):
    #             child_item = item.child(i)
    #             self.fetch_permissions_recursively(child_item)
    #
    #     except Exception as e:
    #         print(f"Error loading permissions for item '{item.text(0)}': {e}")
    # # def copy_selected_items(self):
    # #
    # #     selected_items = self.project_info_list.selectedItems()
    # #     selected_text = "\n".join(item.text() for item in selected_items)
    # #     QApplication.clipboard().setText(selected_text)
    # #
    # # def select_all_items(self):
    # #
    # #     self.project_info_list.selectAll()
