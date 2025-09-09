import toml
import psycopg2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import PIL
import PIL.Image
import PIL.ImageTk
import csv
import easygui

CONFIG = toml.load("./config.toml") # load variables from toml file. 
JAIBA = "la jaiba.png"
CONNECT_STR: str = f'host = {CONFIG['credentials']['host']} dbname = {CONFIG['credentials']['dbname']} user = {CONFIG['credentials']['username']} password = {CONFIG['credentials']['password']}'

class OpenState: # Avoids using global variables
    OPEN: any = True # type: ignore # Keeps track of whether you're looking at open, closed, or all tickets
    SELECTED_ROW: int = 0  
    data: list = [] # list that holds the data the table / treeview is comprised of
    view_cols: list[str] = ['id', 'agent', 'clinic', 'seat', "extension", 'active', 'last_update', 'status', 'remarks'] # default view, currently no way to change this like in the ticket manager
    root: any = None # type: ignore # main window object
    table: any # type: ignore # main table that shows data
    scrollbar: any # type: ignore # vertical scrollbar
    hscrollbar: any # type: ignore # horizontal scrollbar
    main_frame: any # type: ignore # where things get stuffed in the main window object
    button_frame: any # type: ignore # where the buttons go
    image = Image.open("dhr-logo.jpg") # the actual logo
    image_label: any # type: ignore # where the logo goes

def set_open_true():
    OpenState.OPEN = True
    update_data()

def set_open_false():
    OpenState.OPEN = False
    update_data()

def set_all():
    OpenState.OPEN = 'ALL'
    update_data()

def select_row(event):    
    try:
        selected_item = OpenState.table.selection()[0]  # Get the selected item's ID
        if selected_item:
            row_data = OpenState.table.item(selected_item)['values'] # Get data of the selected row
            OpenState.SELECTED_ROW = row_data[0]         
    except:
        OpenState.SELECTED_ROW = 0
    
def add_agent():
    new_agent = easygui.multenterbox(msg = "Enter new agent details.", 
                                     title = "Add Agent", 
                                     fields = ["Name", "Clinic", "Extension", "Seat", "Status", "Remarks"])
    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor()
    query = 'INSERT INTO agents (agent, clinic, extension, seat, status, remarks) VALUES (%s, %s, %s, %s, %s, %s)'
    DATA = tuple(new_agent[i] for i in range(len(new_agent))) # type: ignore
    cur.execute(query, DATA) # type: ignore
    cur.close()
    con.commit()
    easygui.msgbox(title = 'Agent added!', msg = f'Successfully added agent!')
    update_data()

def update_data():
    OpenState.data = [] #if you don't reinitialize this it just adds duplicate entries every time
    refresh_data(OpenState.table, OpenState.data, OpenState.OPEN)

def refresh_data(table, data, open):
    OpenState.SELECTED_ROW = 0
    for item in table.get_children():
        OpenState.table.delete(item)
    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor()
    DATA = (open,)
    if open != 'ALL':
        query = '''SELECT * FROM agents WHERE (agent != 'PENDING' AND active IS %s) ORDER BY 1 ASC;'''
    else:
        query = "SELECT * FROM agents WHERE agent != 'PENDING' ORDER BY id ASC;"
    cur.execute(query, DATA)

    rows = cur.fetchall()
    cur.close()
    con.close()

    for row in rows:
        subresult = []
        for i in range(len(OpenState.view_cols)):
            subresult.append(row[i])
        data.append(subresult)

    for row in data:
        OpenState.table.insert("", tk.END, values=row)

def sort_treeview(tree, col, descending):
    data = [(OpenState.table.set(item, col), item) for item in OpenState.table.get_children('')]
    try:
        data.sort(key = lambda t: int(t[0]), reverse=descending) #special case for ints (like ID)
    except ValueError:
        data.sort(reverse=descending) #all other columns, since you can't int strings :) 
    
    for index, (val, item) in enumerate(data):
        tree.move(item, '', index)
    OpenState.table.heading(col, command = lambda: sort_treeview(tree, col, not descending))

def search():
    OpenState.SELECTED_ROW = 0
    OpenState.data = []
    search_text = easygui.enterbox(title = 'Search', msg = 'Enter search criteria (partial matches will be returned too):', default = '')
    if search_text != None and "jaiba" not in search_text.lower():
        search_text = '%' + search_text + '%'
        for item in OpenState.table.get_children():
            OpenState.table.delete(item)
        con = psycopg2.connect(CONNECT_STR)
        cur = con.cursor()
        DATA = (search_text, search_text, search_text, search_text) #clumsy but works
        cur.execute("""SELECT * FROM agents WHERE 
                    (UPPER(agent) LIKE UPPER(%s) OR
                    UPPER(clinic) LIKE UPPER(%s) OR
                    UPPER(seat) LIKE UPPER(%s) OR
                    UPPER(remarks) LIKE UPPER(%s))
                    ORDER BY id ASC;""", DATA)
        rows = cur.fetchall()

        cur.close()
        con.close()

        for row in rows:
            subresult = []
            for i in range(len(OpenState.view_cols)):
                if row[i] == None:
                    subresult.append("None") # type: ignore
                    
                else:
                    subresult.append(row[i])
            OpenState.data.append(subresult)

        for row in OpenState.data:
            OpenState.table.insert("", tk.END, values=row)
    elif "jaiba" in search_text.lower():
        la_jaiba()
    else:
        pass

def toggle_agent():
    if OpenState.SELECTED_ROW == 0:
        easygui.msgbox(title = 'No agent Selected', 
               msg = 'You need to select an agent!') 
    else:
        con = psycopg2.connect(CONNECT_STR)
        cur = con.cursor()
        cur.execute(f"SELECT active FROM agents WHERE id = {OpenState.SELECTED_ROW};")
        result = cur.fetchone()
        if result[0] == True: # type: ignore
            new_state = False
        if result[0] == False: # type: ignore
            new_state = True
        data = (new_state, OpenState.SELECTED_ROW) # type: ignore
        query = "UPDATE agents SET active = %s WHERE id = %s;"
        cur.execute(query, data)
        cur.close()
        con.commit()
        easygui.msgbox(title = "Update complete!", msg = "Agent status has been changed successfully.")
    update_data()

def update_status(event = None):
    if OpenState.SELECTED_ROW == 0:
        easygui.msgbox(title = 'No agent Selected', 
               msg = 'You need to select an agent!')    
    else:
        choice = easygui.choicebox(title = "Update", 
                                   msg = "What did you want to update?", 
                                   choices = ["Agent Name", "Clinic", "Extension", "Status", "Seat", "Toggle Active/Inactive", "Status", "Remarks"]
                                   )
        match choice:
            case "Agent Name":
                try:
                    new_name: str | None  = easygui.enterbox(title = "New Agent Name", msg = "Enter new name:").upper()
                except:
                    new_name = None
                if new_name:
                    con = psycopg2.connect(CONNECT_STR)
                    cur = con.cursor()
                    cur.execute('SELECT agent FROM agents WHERE id = %s', (OpenState.SELECTED_ROW,))
                    result: tuple | None = cur.fetchone()
                    data = (new_name, OpenState.SELECTED_ROW, result[0]) # type: ignore
                    query = "UPDATE agents SET agent = %s WHERE (id = %s and agent = %s);"
                    cur.execute(query, data)
                    cur.close()
                    con.commit()
                    easygui.msgbox(title = "Update complete!", msg = "Agent name successfully updated!")
                    update_data()
                else:
                    easygui.msgbox(title = "Update cancelled", msg = "Agent name update cancelled.")
            case "Clinic":
                try:
                    new_clinic: str | None= easygui.enterbox(title = "New Clinic Name", msg = "Enter new clinic name:").upper()
                except:
                    new_clinic = None
                if new_clinic:
                    con = psycopg2.connect(CONNECT_STR)
                    cur = con.cursor()
                    cur.execute('SELECT agent FROM agents WHERE id = %s', (OpenState.SELECTED_ROW,))
                    result: tuple | None = cur.fetchone()
                    data = (new_clinic, OpenState.SELECTED_ROW, result[0]) # type: ignore
                    query = "UPDATE agents SET clinic = %s WHERE (id = %s AND agent = %s);"
                    cur.execute(query, data)
                    cur.close()
                    con.commit()
                    easygui.msgbox(title = "Update complete!", msg = "Clinic successfully updated.")
                    update_data()
                else:
                    easygui.msgbox(title = "Update cancelled.", msg = "Clinic update cancelled.")
            case "Extension":
                try:
                    new_extension: str | None = easygui.enterbox(title = "New Extension", msg = "Enter new extension:")
                except:
                    new_extension = None
                if new_extension:
                    con = psycopg2.connect(CONNECT_STR)
                    cur = con.cursor()
                    data = (new_extension, OpenState.SELECTED_ROW) # type: ignore
                    query = "UPDATE agents SET extension = %s WHERE id = %s;"
                    cur.execute(query, data)
                    cur.close()
                    con.commit()
                    easygui.msgbox(title = "Update complete!", msg = "Extension successfully updated.")
                    update_data()
                else:
                    easygui.msgbox(title = "Update cancelled", msg = "Extension update cancelled.")
            case "Toggle Active/Inactive":
                con = psycopg2.connect(CONNECT_STR)
                cur = con.cursor()
                query = "SELECT active FROM agents WHERE id = %s;"
                data = (OpenState.SELECTED_ROW, )
                cur.execute(query, data)
                result = cur.fetchone()
                if result[0] == True: # type: ignore
                    new_state = False
                if result[0] == False: # type: ignore
                    new_state = True
                data = (new_state, OpenState.SELECTED_ROW) # type: ignore
                query = "UPDATE agents SET active = %s WHERE id = %s;"
                cur.execute(query, data)
                cur.close()
                con.commit()
                easygui.msgbox(title = "Update complete!", msg = "Agent status has been changed successfully.")
                update_data()
            case "Seat":
                try:
                    new_seat: str | None = easygui.enterbox(title = "New Seat", msg = "Enter new seat (refer to map):")
                except:
                    new_seat = None
                if new_seat:
                    con = psycopg2.connect(CONNECT_STR)
                    cur = con.cursor()
                    data = (new_seat, OpenState.SELECTED_ROW)
                    query = "UPDATE agents SET seat = %s WHERE id = %s;"
                    cur.execute(query, data)
                    cur.close()
                    con.commit()
                    easygui.msgbox(title = "Update complete!", msg = "Seat successfully updated.")
                    update_data()
                else:
                    easygui.msgbox(title = "Update cancelled", msg = "Seat update cancelled.")
            case "Remarks":
                try:
                    new_remarks: str | None = easygui.enterbox(title = "Update Remarks", msg = "Enter new remarks. This will overwrite current remarks.")
                except:
                    new_remarks = None
                if new_remarks:
                    con = psycopg2.connect(CONNECT_STR)
                    cur = con.cursor()
                    data = (new_remarks, OpenState.SELECTED_ROW) # type: ignore
                    query = "UPDATE agents SET remarks = %s WHERE id = %s;"
                    cur.execute(query, data)
                    cur.close()
                    con.commit()
                    easygui.msgbox(title = "Update complete!", msg = "Remarks successfully updated.")
                    update_data()
                else:
                    easygui.msgbox(title = "Update cancelled", msg = "Remarks update cancelled.")
            case "Status":
                try:
                    new_status: str | None= easygui.enterbox(title = "Update Status", msg = "Enter new status. This will overwrite current remarks.")
                except:
                    new_status = None
                if new_status:
                    con = psycopg2.connect(CONNECT_STR)
                    cur = con.cursor()
                    data = (new_status, OpenState.SELECTED_ROW) # type: ignore
                    query = "UPDATE agents SET status = %s WHERE id = %s;"
                    cur.execute(query, data)
                    cur.close()
                    con.commit()
                    easygui.msgbox(title = "Update complete!", msg = "Status successfully updated.")
                    update_data()
                else:
                    easygui.msgbox(title = "Update cancelled", msg = "Status update cancelled.")

def la_jaiba():
    
    def resize_event(event): 
        resized = PIL.ImageTk.PhotoImage(img.resize((event.width, event.height)))
        canvas.itemconfig(img_item, image=resized)
        canvas.moveto(img_item, 0, 0)
        canvas.image = resized # type: ignore
    
    map= tk.Toplevel()
    map.resizable(True, True)
    map.title('LA JAIBA!')
    img = PIL.Image.open(JAIBA)
    photo = PIL.ImageTk.PhotoImage(img)
    canvas= tk.Canvas(map, width = 225, height = 225) 
    img_item = canvas.create_image(0, 0, image = photo)
    canvas.bind('<Configure>', resize_event)
    canvas.pack(expand=True, fill='both')
    map.mainloop()

def display_map():
    floorplan: str = 'Python Plan.png'
    def resize_event(event):
        resized = PIL.ImageTk.PhotoImage(img.resize((event.width, event.height)))
        canvas.itemconfig(img_item, image=resized)
        canvas.moveto(img_item, 0, 0)
        canvas.image = resized # type: ignore
    
    map= tk.Toplevel()
    map.resizable(True, True)
    map.title('Floor Map')
    img = PIL.Image.open(floorplan)
    photo = PIL.ImageTk.PhotoImage(img)
    canvas= tk.Canvas(map, width = 1600, height = 900) 
    img_item = canvas.create_image(0, 0, image = photo)
    canvas.bind('<Configure>', resize_event)
    canvas.pack(expand=True, fill='both')
    map.mainloop()

def generate_report():    
    output = easygui.filesavebox(title = 'Select filename and location to save report',
                          default='report.csv', 
                          filetypes = '*.csv')

    with open(output, 'w', newline = '') as report: # type: ignore
        writer = csv.writer(report)
        writer.writerow(OpenState.view_cols)
        for row in OpenState.data:
            writer.writerow(row)

def create_window(): #assemble the actual window and buttons the user interacts with
    if not OpenState.root:
        OpenState.root = tk.Tk()
        OpenState.root.minsize(1200, 475)
        OpenState.root.title("Agent Viewer and Editor")

    OpenState.main_frame = ttk.Frame(OpenState.root)
    OpenState.main_frame.pack(pady=10)

    OpenState.table = ttk.Treeview(OpenState.root, columns=OpenState.view_cols, selectmode='browse', show="headings", height=20)
    OpenState.table.pack(side=tk.LEFT, fill=tk.BOTH, expand = True)

    # Define column headings
    for column in OpenState.view_cols:
        OpenState.table.heading(f'{column}', text=f'{column}', anchor = tk.CENTER, command = lambda c = f'{column}': sort_treeview(OpenState.table, c, False))
        OpenState.table.column(column, anchor=tk.CENTER, width = 80)
    OpenState.table.update()
    for column in OpenState.table['columns']:
        OpenState.table.column(column, width = 100, stretch = 0)

    OpenState.scrollbar = ttk.Scrollbar(OpenState.root, orient=tk.VERTICAL, command=OpenState.table.yview)
    OpenState.scrollbar.pack(side=tk.LEFT, fill=tk.Y)

    OpenState.hscrollbar = ttk.Scrollbar(OpenState.table, orient=tk.HORIZONTAL, command=OpenState.table.xview)
    OpenState.hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    OpenState.table.configure(yscrollcommand=OpenState.scrollbar.set)
    OpenState.table.configure(xscrollcommand=OpenState.hscrollbar.set)

    # Button Frame
    OpenState.button_frame = ttk.Frame(OpenState.root)
    OpenState.button_frame.pack(side=tk.TOP, pady = 10)

    # Actual Buttons
   
    map_display_button = ttk.Button(OpenState.button_frame, text="Open Map", command=display_map)
    map_display_button.pack(padx = 5, pady = 5)

    search_button = ttk.Button(OpenState.button_frame, text="Search", command=search)
    search_button.pack(padx = 5, pady = 5)

    refresh_button = ttk.Button(OpenState.button_frame, text="Refresh", command=update_data)
    refresh_button.pack(padx = 5, pady = 5)

    add_agent_button = ttk.Button(OpenState.button_frame, text="Add Agent", command=add_agent)
    add_agent_button.pack(padx = 5, pady = 5)

    toggle_button = ttk.Button(OpenState.button_frame, text="Toggle Agent Active Status", command=toggle_agent)
    toggle_button.pack(padx = 5, pady = 5)

    view_active_agents_button = ttk.Button(OpenState.button_frame, text = 'Show Active Agents', command = set_open_true)
    view_active_agents_button.pack(padx = 5, pady = 5)

    view_inactive_agents_button = ttk.Button(OpenState.button_frame, text = 'Show Inactive Agents', command = set_open_false)
    view_inactive_agents_button.pack(padx = 5, pady = 5)

    view_all_agents_button = ttk.Button(OpenState.button_frame, text = 'Show All Agents', command = set_all)
    view_all_agents_button.pack(padx = 5, pady = 5)

    update_selected_agent_button = ttk.Button(OpenState.button_frame, text = 'Update Agent', command = update_status)
    update_selected_agent_button.pack(padx = 5, pady = 5) 

    report_button = ttk.Button(OpenState.button_frame, text = 'Generate Report of Current View', command = generate_report)
    report_button.pack(padx = 5, pady = 5)

    # Load DHR logo
    OpenState.image = Image.open("dhr-logo.jpg")
    resized_image = OpenState.image.resize((400, 110))
    photo = ImageTk.PhotoImage(resized_image)
    OpenState.image_label = tk.Label(OpenState.main_frame, image=photo)
    OpenState.image_label.image = photo # Keep a reference to prevent garbage collection
    OpenState.image_label.pack(side = tk.BOTTOM)

    # Initial table population
    refresh_data(OpenState.table, OpenState.data, OpenState.OPEN)

    # Mouse button bindings (bound to the table)
    OpenState.table.bind("<ButtonRelease-1>", select_row)  # Call select_row on mouse click
    OpenState.table.bind("<ButtonRelease-3>", update_status) # Calls update_status on right click if an agent is selected
    OpenState.table.pack()

create_window()
OpenState.root.mainloop()