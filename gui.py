from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QListWidget, QProgressBar, QFileDialog,
    QLineEdit, QShortcut, QPushButton, QCheckBox, QApplication, QHBoxLayout, QTreeWidget, QTreeWidgetItem
)
import qtawesome as qta
import os
from permissions import (
    store_all_permissions_only_as_dict_multithreaded, store_user_permissions_only_as_dict_multithreaded, store_group_permissions_only_as_dict_multithreaded
)


class TestGUI(QMainWindow):
    class FolderPermissionWorker(QThread):
        progress_update = pyqtSignal(int)  # Signal for reporting progress
        tree_data_ready = pyqtSignal(dict)  # Signal for task completion (total time and report file)

        def __init__(self, root_path, method = "all"):
            super().__init__()
            self.root_path = root_path  # The root path for processing
            self.method = method

        def run(self):
            def progress_callback(current, total):
                # Calculate the percentage progress
                if total > 0:
                    progress_percentage = int((current / total) * 100)
                    self.progress_update.emit(progress_percentage)

            # -----------------------------Got rid of to use only tree widget------------------------#
            # Decide which function to call based on the method type
            #if self.method == "users_only":
               # total_time, report_file = print_all_user_permission(
               #     self.root_path, progress_callback)
            #elif self.method == "groups_only":
                #total_time, report_file = print_all_groups_permission(
                   # self.root_path, progress_callback)
            #else: # Default to all_permissions
              #  total_time, report_file = print_all_principal_permission(
               #     self.root_path, progress_callback)

            # Emit the signal for task completion when done
            #self.task_completed.emit(total_time, report_file)
            # -------------------------------------------------------------------------------------#

            if self.method == "users_only":
                folder_permissions = store_user_permissions_only_as_dict_multithreaded(self.root_path, max_workers=8)
            elif self.method == "groups_only":
                folder_permissions = store_group_permissions_only_as_dict_multithreaded(self.root_path)
            else:  # Default: "all"
                folder_permissions = store_all_permissions_only_as_dict_multithreaded(self.root_path)

            # Emit progress as complete
            self.progress_update.emit(100)

            # Send data to the GUI
            self.tree_data_ready.emit(folder_permissions)

    def __init__(self):
        super().__init__()
        self.start_gui()

    def start_gui(self):
        # Set up a window
        self.setWindowTitle("Folder Permissions GUI")
        #Adds the fullscreen/minimize/close in the top right of the gui
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.setGeometry(100,100,2000,975)


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

        # Folder Path Input
        folder_path_label = QLabel("Enter Folder Path:")
        layout.addWidget(folder_path_label)

        # Allows items on the same line
        self.horizontal_layout = QHBoxLayout()
        layout.addLayout(self.horizontal_layout)

        # Input line with a file path
        self.file_path_input = QLineEdit()
        self.horizontal_layout.addWidget(self.file_path_input)

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

        self.show_groups_checkbox = QCheckBox("Include Groups")
        self.show_groups_checkbox.setChecked(False)
        layout.addWidget( self.show_groups_checkbox)

        self.show_users_checkbox = QCheckBox("Include Users")
        self.show_users_checkbox.setChecked(True)
        layout.addWidget( self.show_users_checkbox)

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
        self.tree_widget.setHeaderLabels(["Folder","User","Permissions", "Inheritance","Type","Folder Owner"])

        self.tree_widget.setColumnWidth(0, 250)
        self.tree_widget.setColumnWidth(1, 250)
        self.tree_widget.setColumnWidth(2, 175)
        self.tree_widget.setColumnWidth(3, 550)
        self.tree_widget.setColumnWidth(4, 300)
        self.tree_widget.setColumnWidth(5, 250)
        layout.addWidget(self.tree_widget)

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

        #-----------------------------Got rid of to use only tree widget------------------------#
        #Label with file location
        #self.file_location_label = QLabel("File Location:")
        #layout.addWidget(self.file_location_label)
        #self.file_path = QLineEdit()
        #layout.addWidget(self.file_path)
        # --------------------------------------------------------------------------------------

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

    def update_tree_widget(self, folder_permissions):
        self.tree_widget.clear()

        #Dict to store which folders become children of other folders in the tree
        tree_data = {}

        # Build the tree_data dictionary
        for folder, permissions in folder_permissions.items():
            parts = folder.split("\\") #splits folder_path
            first_part = parts[0] #This is the top branch

            #If it doesn't exist in tree_data, add it
            if first_part not in tree_data:
                tree_data[first_part] = {"permissions": [], "subfolders": {}}
                # Permission holds rules while subfolder hold child branches


            current_level = tree_data[first_part]
            for part in parts[1:]:
                if part not in current_level["subfolders"]:
                    current_level["subfolders"][part] = {"permissions": [], "subfolders": {}}

                #moves to branch with subfolder and inserts it
                current_level = current_level["subfolders"][part]

            #Once all subfolders are done, add the permissions
            current_level["permissions"].extend(permissions)

        def add_items(parent_item, folder_data):
            # List that will hold all the branches, starts with just the parent branch and its data
            holder_list = [(parent_item, folder_data)]

            while holder_list:
                current_parent, current_data = holder_list.pop()

                # Iterate through folders at the current branch
                for folder_name, folder_details in current_data.items():
                    if folder_name == "permissions":
                        continue

                    # Extract owner for this branch
                    branch_owner = folder_details["permissions"][0][4] if folder_details["permissions"] else "No Owner"

                    # Create a new tree branch and display the owner once on this branch
                    folder_item = QTreeWidgetItem([folder_name, "", "", "", "", f"       {branch_owner}"])

                    current_parent.addChild(folder_item)

                    # Add permissions for this branch
                    for user1, perm1, source1, type1, _ in folder_details["permissions"]:
                        permission_item1 = QTreeWidgetItem(
                            ["", f"{user1}", f"     {perm1}", f"{source1}", f"{type1}", ""]
                        )
                        folder_item.addChild(permission_item1)

                    # Adds the branch to the hold list if the folder has subfolders
                    holder_list.append((folder_item, folder_details["subfolders"]))

        # Starts filling the tree widget
        for top_folder, details, in tree_data.items():
            # Extract the owner of the top-level folder
            top_owner = details["permissions"][0][4] if details["permissions"] else "No Owner"

            #
            top_item = QTreeWidgetItem([top_folder, "", "", "", "", top_owner])
            self.tree_widget.addTopLevelItem(top_item)

            # Add permissions for the top-level
            for user, perm, source, type, _ in details["permissions"]:
                permission_item = QTreeWidgetItem(
                    ["", f"{user}", f"     {perm}", f"{source}", f"{type}", ""]
                )
                top_item.addChild(permission_item)

            # Add subfolders
            add_items(top_item, details["subfolders"])

        self.progress_bar.setValue(100)

    def search_tree_1(self):
        search_term = self.search_tree.text().strip()
        if not search_term:
            self.show_error_message("Please enter a search term.")
            return

        search_term = search_term.lower()

        self.highlight_searched_item(self.tree_widget, search_term)

    def highlight_searched_item(self,tree_widget,search_term):

        for i in range(tree_widget.topLevelItemCount()):
            top_item = tree_widget.topLevelItem(i)
            self.search_items(top_item, search_term)

    def search_items(self, item, search_term):
        # Reset item background color by default
        item.setBackground(0, Qt.transparent)
        item.setBackground(1, Qt.transparent)
        item.setBackground(2, Qt.transparent)

        # Check if any column text contains the search term
        for col in range(item.columnCount()):
            if search_term in item.text(col).lower():
                # Highlight the matching item
                item.setBackground(col, Qt.yellow)


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
        file_path_input = self.file_path_input.text().strip()
        if not file_path_input or not os.path.exists(file_path_input):
            self.show_error_message("Invalid folder path.")
            return

        try:
            include_groups = self.show_groups_checkbox.isChecked()
            include_users = self.show_users_checkbox.isChecked()

            # db_connection = connect_db()
            # if db_connection:
            # Fetch and display project details
            self.progress_bar.setValue(15)
            # project_info = get_project_info(file_path_input, db_connection)
            # self.display_project_info(project_info)

            #self.fill_tree(file_path_input)

            if include_users and not include_groups:
                method = "users_only"
                print("Only users")
            elif include_groups and not include_users:
                method = "groups_only"
                print("Only groups")
            else:
                method = "all"
                print("Both users and groups")

            # Start the worker thread
            self.worker = self.FolderPermissionWorker(file_path_input,method)
            self.worker.progress_update.connect(self.update_progress_bar)  # Connect progress updates
            self.worker.tree_data_ready.connect(self.update_tree_widget)  # Connect tree data
            self.worker.start()  # Start the worker thread


        except Exception as e:
            print(F"An error occurred: {e}")

    def display_project_info(self, project_info):
        self.project_info_list.clear() # Clears the listbox before starting
        if not project_info:
            self.project_info_list.addItem("No project found.")
            return

        for row in project_info:
            project_number = row[0]
            project_name = row[1]
            emp_name = row[2]
            division_name = row[3]
            division_admin = row[4]

        self.project_info_list.addItem(f"Project Number: {project_number}")
        self.project_info_list.addItem(f"Project Name: {project_name}")
        self.project_info_list.addItem(f"Employee Name: {emp_name}")
        self.project_info_list.addItem(f"Division Name: {division_name}")
        self.project_info_list.addItem(f"Division Admin: {division_admin}")

    def update_progress_bar(self, value):

        self.progress_bar.setValue(value)

    def copy_selected_items(self):

        selected_items = self.project_info_list.selectedItems()
        selected_text = "\n".join(item.text() for item in selected_items)
        QApplication.clipboard().setText(selected_text)

    def select_all_items(self):

        self.project_info_list.selectAll()