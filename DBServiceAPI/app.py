from flask import Flask, g,render_template, request,abort, redirect, url_for, flash, session, make_response,jsonify
from Dir_MyClasses.oracle_class import OracleUtils
from Dir_MyClasses.users import User
from Dir_MyClasses.table_or_view_class import TableOrView
from Dir_MyClasses.services import AuthService
from config.Config import ConfigClass
import json
import os
from datetime import datetime
import requests  
#from flask_caching import Cache
#from urllib.parse import parse_qs

app = Flask(__name__, template_folder='Dir_Html_Templates')

# Add enumerate to Jinja2 environment
app.jinja_env.globals.update(enumerate=enumerate)

app.secret_key = 'Vdsgvvkgio2000$' 
#cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})
app.config['JSON_AS_ASCII'] = False

config_folder = 'config'
config_path = os.path.join(config_folder,'Config.ini')

CONFIG = ConfigClass(config_path)

AUTH_BASE_URL = CONFIG.get_value('AuthService','base_url')

ORACLE_CONFIG = {}
ORACLE_CONFIG['username'] = CONFIG.get_value('Oracle','username')
ORACLE_CONFIG['password'] = CONFIG.get_value('Oracle','password')
ORACLE_CONFIG['host'] = CONFIG.get_value('Oracle','host')
ORACLE_CONFIG['port'] = CONFIG.get_value('Oracle','port')
ORACLE_CONFIG['service_name'] = CONFIG.get_value('Oracle','service_name')

USERS = {"admin": "password123" }

TableOrView_objs = {}   # თუ მონაცემები არ არის, დაიწყება ნული
#O_About = TableOrView('PSARALIDZE.VIEW_ABOUT')
#TableOrView_objs['PSARALIDZE.VIEW_ABOUT'] = O_About
last_loaded = 0  # დროის მარკერი
CACHE_LIFETIME = 3600*24  # გარკვეული დროის შემდეგ მოხდეს მონაცემების განახლება (წამებში)

def add_TableOrView_data(name,ORACLE_CONFIG):
    global TableOrView_objs
    if name not in TableOrView_objs:
        obj = TableOrView(name,ORACLE_CONFIG) 
        TableOrView_objs[name] = obj   # დაამატე ახალი ობიექტი

# ბაზიდან მონაცემების გადმოწერა
#def load_TableOrView_db():
    # فرბაზიდან მონაცემების გადმოწერა
#   return [MyClass("data1"), MyClass("data2"), MyClass("data3"


def get_db_connection():
    if 'db' not in g:
        g.db = OracleUtils(ORACLE_CONFIG['username'],ORACLE_CONFIG['password'],ORACLE_CONFIG['host'],ORACLE_CONFIG['port'],ORACLE_CONFIG['service_name'])   
    return g.db

def get_alias_dict():
    if 'ALIAS_DICT' not in g:
       g.ALIAS_DICT = create_alias_dict()
    return g.ALIAS_DICT

def create_alias_dict():
    dict_alias = {}
   
    DCC = get_db_connection()
    # მონაცემთა ბაზიდან შესაბამისი სვეტების ამოღება
    aliass, columns = DCC.get_dict_by_dba_select(
        f"""SELECT COLUMN_NAME, COLUMN_ALIAS FROM PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature
        where TABLE_OR_VIEW = upper('{session['view_table']}')
        """
    )
      
    for alias in aliass:
        column_name = alias[columns[0]]
        column_alias = alias[columns[1]]
        
        # თუ COLUMN_NAME დიქშენარში არ არსებობს, პირდაპირ ვამატებთ
        if column_name not in dict_alias:
            dict_alias[column_name] = column_alias
        else:
            # თუ COLUMN_ALIAS უკვე არსებობს და ტოლია COLUMN_NAME-ის, ვანაცვლებთ
            if dict_alias[column_name] == column_name:
                dict_alias[column_name] = column_alias        

    # JSON ფორმატში გარდაქმნა
    dict_alias_json = json.dumps(dict_alias, ensure_ascii=False, indent=4)
    return dict_alias_json

def refresh_views(p_table_or_view ,p_operations):

    DCC = get_db_connection()

    exec_procedure = f"""begin 
            PSARALIDZE.sp_EXEC_TABLE_OR_VIEW_feature ( upper('{p_table_or_view}')  ,'{p_operations}');
            end;"""
        
    result = DCC.dba_insert_update_query(exec_procedure)   

    return result
   

def get_views():
    views = []
    
    DCC = get_db_connection()
    # მონაცემთა ბაზიდან შესაბამისი სვეტების ამოღება
    vws, columns = DCC.get_dict_by_dba_select(
        f""" SELECT distinct TABLE_OR_VIEW 
        FROM PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature   order By   TABLE_OR_VIEW   
       """    )           
    for view in vws:
       views.append(view[columns[0]])  

    view_new = []
    i = 0       
    while True:
        v = CONFIG.get_value('VIEWS', f'VIEW_{i}')        
        if v:                     
            if v.upper() not in views:                
                view_new.append(v)                
            i += 1
        else:
            break  # Exit the loop if no view is found   

    if len(view_new) > 0:
        exec_procedure = f"""begin 
            PSARALIDZE.sp_EXEC_TABLE_OR_VIEW_feature ( upper('{view_new[0]}')  ,'01234');
            end;"""
        
        result = DCC.dba_insert_update_query(exec_procedure)   
    return views

def get_alias(OBJ_NAME,alias_dict):
   if OBJ_NAME in alias_dict:
    return alias_dict[OBJ_NAME]
   else: 
    return OBJ_NAME
   
def get_columns_alias(columns,alias_dict):
   
   columns_alias = []
   for COLUMN_NAME in columns:     
     if COLUMN_NAME in alias_dict:       
       columns_alias.append(alias_dict[COLUMN_NAME])
     else: columns_alias.append(COLUMN_NAME)

   return columns_alias
 

@app.before_request
def restrict_ip():
    ip_address = request.remote_addr
    # შეამოწმეთ, არის თუ არა IP მისამართი არ 192.168.x.x
    if not ip_address.startswith('192.168'):
     abort(403)  # აკრძალეთ წვდომა, 403 Forbidden

@app.route('/dropdown_list', methods=['GET'])
def get_dropdown_list():
    
        dropdown_uniq_id = request.args.get('dropdown_uniq_id','CCARE_BPMN.TMS_MATERIALIZED_TASKS.9')  # პარამეტრის მიღება
        
       
        parts = dropdown_uniq_id.split(".")
        
        if len(parts) == 3:
            owner = parts[0]
            table_view = parts[1]
            column_id = parts[2]
        else:
            return jsonify({f"error": f"Invalid dropdown_uniq_id format : {dropdown_uniq_id}"})
        
        if owner + '.' + table_view not in get_views():
            DCC = get_db_connection()
            exec_procedure = f"""begin 
            PSARALIDZE.sp_EXEC_TABLE_OR_VIEW_feature(upper('{owner + '.' + table_view}'),'01234');
            end;"""        
            result = DCC.dba_insert_update_query(exec_procedure)   
            return jsonify({f"error": f"Invalid view_name : {result}",f"exec_procedure": f"Invalid view_name : {exec_procedure}"})      


        # მონაცემების წამოღება დროპდაუნის სახელის მიხედვით
        query = ""
        if len(dropdown_uniq_id)  > 5:
            query = f"""SELECT f.SAMPLE_LIST_JSON,f.COLUMN_UNIQ_ID,f.COLUMN_NAME  FROM PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature f 
                    WHERE f.column_uniq_id = '{dropdown_uniq_id}' and FEATURE_ID = 1
                    """        
        else:
            return jsonify({f"error": f"Invalid dropdown_uniq_id : {dropdown_uniq_id}"})

        conn = get_db_connection()
        rows,columns = conn.get_dict_by_dba_select(query)        
        
        if rows:
            for row in rows:
                COLUMN_NAME = columns[2]
                column_uniq_id =  row['COLUMN_UNIQ_ID']
                my_json = row['SAMPLE_LIST_JSON']
            return jsonify({COLUMN_NAME:my_json})
        else:
            return jsonify({f"error": f"Invalid dropdown_uniq_id : {dropdown_uniq_id}"})
        
        

        # მონაცემების JSON ფორმატში გადაყვანა
        #data = [{'id': r[0], 'name': r[0]} for r in my_json]
        

    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        User_Log = User() 

        auth_service = AuthService()
        auth_service.set_base_url(AUTH_BASE_URL)
        success = auth_service.login(username, password)
        token = auth_service.get_token()
        if success:
          session['username'] = username
          session['token'] = token
          session['view_table_changed'] = 1
          session['view_table'] = 'PSARALIDZE.VIEW_ABOUT'
          User_Log.set_username(session['username'],ORACLE_CONFIG)
          session['user_permitions'] = json.dumps(User_Log.user_permitions) 
          return redirect(url_for('index'))
             
        else:
           # Check if the username and password match the sample user
           if username in USERS and USERS[username] == password:
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
           else:
            flash(f'Invalid username or password {password}', 'danger')
#exit(0)
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():       

    if request.method == 'POST':
     view_table = str(request.form.get("view_table", ""))
    else:
     view_table = str(request.args.get("view_table", "")) 
    
    

    if view_table == "": 
      session['view_table_changed'] = 1
      session['view_table'] = 'PSARALIDZE.VIEW_ABOUT' 
    
    if view_table != session['view_table']:
       session['view_table_changed'] = 1
    else: 
       session['view_table_changed'] = 0

    session['view_table'] = view_table 

    if view_table:
        return redirect(url_for('index'))

def update_view_feature(column_id,feature_id,  filter_flag, view_flag,COLUMN_UNIQ_ID,COLUMN_ALIAS, ORDERING,CONSTRAINT_TYPE):

    view_table = session.get('view_table')

    num_distinct = 0


    if filter_flag == "on":
       flter_flag = 1
    else:
       flter_flag = 0
       num_distinct = 999

    if view_flag == "on":
       vw_flag = 1
    else:
       vw_flag = 0

    

    query_update = f"""       
        UPDATE PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature f 
        SET FEATURE_ID = '{feature_id}'
        ,FILTER_FLAG = {flter_flag}
        ,VIEW_FLAG = {vw_flag}
        ,COLUMN_ALIAS = '{COLUMN_ALIAS}'
        ,ORDERING = {ORDERING}
        ,CONSTRAINT_TYPE = '{CONSTRAINT_TYPE}'
        ,num_distinct = case when {num_distinct} > 0 then {num_distinct}  else num_distinct end
        ,SAMPLE_LIST_JSON = case when {num_distinct} > 0 then null  else SAMPLE_LIST_JSON end
        WHERE  COLUMN_UNIQ_ID = '{COLUMN_UNIQ_ID}'    
        """
    OrcUtil = get_db_connection()     

    

    OrcUtil.dba_insert_update_query(query_update)

    # update SAMPLE_LIST_JSON
    if column_id == 1:
        query_JSON = f"""       
            SELECT COLUMN_NAME            
            FROM PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature f 
            WHERE 1=1 
            and f.feature_id = 1 and (f.num_distinct < 600 or  f.num_distinct = 999 )
            and f.sample_list_json is null
            and TABLE_OR_VIEW = upper('{view_table}')
            ORDER BY TABLE_OR_VIEW, COLUMN_ID 
            """
        rws,flds = OrcUtil.get_dict_by_dba_select(query_JSON)

        if rws:  
            column_name = rws[0][flds[0]]

            query_JSON = f"""       
                SELECT distinct {column_name}       
                FROM {view_table} rt
                where {column_name} is not null
                ORDER BY {column_name}     
                """
            rw,fld = OrcUtil.get_dict_by_dba_select(query_JSON,0,3000)
            
            list_for_json = []
            for r in rw:
               list_for_json.append(r[fld[0]])

            list_json = json.dumps(list_for_json, indent=4, ensure_ascii=False)

           
            
            OrcUtil.write_json_in_oracle(list_json,view_table,column_name) 

           
@app.route('/ManageView', methods=['GET', 'POST'])
def ManageView():
   
    if 'username' not in session:
        flash('Please log in to access the page.', 'warning')
        return redirect(url_for('login'))  
    
    VIEWS = get_views()
    table = VIEWS[0]  
    
    user_name = session["username"]     
    token = session["token"]   
    user_permitions = session['user_permitions']   
    view_table = session.get('view_table', table)

    column_count = 1
    feature_ids = []
    filter_flags = []
    view_flags = []
    COLUMN_UNIQ_IDs = []
    COLUMN_ALIASs = []
    ORDERINGs = []
    CONSTRAINT_TYPEs = []
    
    if request.method == 'POST':    
       while  request.form.get(f"FEATURE_ID_{column_count}",-1) != -1 and column_count  < 200: 
        feature_ids.append(request.form.get(f"FEATURE_ID_{column_count}",""))
        filter_flags.append(request.form.get(f"FILTER_FLAG_{column_count}",""))
        view_flags.append(request.form.get(f"VIEW_FLAG_{column_count}",""))
        COLUMN_UNIQ_IDs.append(request.form.get(f"COLUMN_UNIQ_ID_{column_count}",""))
        COLUMN_ALIASs.append(request.form.get(f"COLUMN_ALIAS_{column_count}",""))
        ORDERINGs.append(request.form.get(f"ORDERING_{column_count}",""))
        CONSTRAINT_TYPEs.append(request.form.get(f"CONSTRAINT_TYPE_{column_count}",""))
        column_count += 1

    for i in range(len(feature_ids)):
        update_view_feature(i+1,feature_ids[i], filter_flags[i], view_flags[i], COLUMN_UNIQ_IDs[i], COLUMN_ALIASs[i], ORDERINGs[i], CONSTRAINT_TYPEs[i])    
    
    query = f"""SELECT COLUMN_ID,COLUMN_NAME,COLUMN_ALIAS,ORDERING,FEATURE_ID,FILTER_FLAG,VIEW_FLAG,CONSTRAINT_TYPE
        ,COLUMN_DATA_TYPE, NUM_DISTINCT, SAMPLE_SIZE,SAMPLE_LIST_JSON,column_uniq_id
        FROM PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature f 
        WHERE  TABLE_OR_VIEW = upper('{view_table}')
        ORDER BY COLUMN_ID
        """
    OrcUtil = get_db_connection()     
    rows, column_names = OrcUtil.get_dict_by_dba_select(query,0,500)

    permision = f"{view_table}_ADMIN"
    
    #permissions = eval(CONFIG.get_value('permissions','permissions_v_0'))

    view_table_last_part = view_table.split('.')[-1] if '.' in view_table else "0"
    welcome = f"... Manage View : {view_table_last_part}"
    #welcome = f"... Manage View : {view_table}"

    if all(perm not in user_permitions for perm in permision):
       welcome = f" N/A permision : {permision} in : {user_permitions}"
       view_table = None   

    

    return render_template('manageview.html', view_table=view_table,view = VIEWS,welcome = welcome,user_name=user_name, rows=rows, column_names=column_names) 


@app.route('/singlrowupdate', methods=['POST'])
def singlrowupdate():
    try:
        # Parse incoming JSON data from the request body
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Example: Process data (Replace with your logic)
        view_table = data.get('view_table', '')
        fields = {key: value for key, value in data.items() if key != 'view_table'}
        
        ii = 0
        set_clause = f" SET "
        for key in fields.keys():
            if ii == 0:
                set_where = f" where {key} = '{fields.get(key)}'"
            else:   
                if  ii == 1:  
                    set_clause = set_clause + f" {key} = '{fields.get(key)}'"
                else: 
                    set_clause = set_clause + f", {key} = '{fields.get(key)}'"
            ii += 1
        
        query = f""" update  {view_table} {set_clause} {set_where}"""

        print(f"Updating table query:  {query}")

        conn = get_db_connection()
        conn.dba_insert_update_query(query)
        # Simulate an update operation (e.g., updating a database)        
        
        
        # Return a success response
        return jsonify({"message": "Row updated successfully", "updated_data": data}), 200
    
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500
   

@app.route('/singlrowview', methods=['POST'])
def singlrowview():    

    if 'username' not in session:
        flash('Please log in to access the page.', 'warning')
        return redirect(url_for('login'))  
    
    VIEWS = get_views()
    table = VIEWS[0]  
    
    user_name = session["username"]     
    token = session["token"]   
    user_permitions = session['user_permitions']   
    view_table = session.get('view_table', table)

    welcome = f"ქმედების გვერდი"

    rows = None
    column_names = None
    total = 1
   
    fields,dd_fields,filter_values,dt_fields,view_filds = get_view_fields(view_table)
   
    date_list = {}
    for fild in view_filds:
        date_list[fild] = request.form.get(fild, "")
    date_list['view_table'] = view_table

    base_url = 'http://192.168.54.11:8080'
    api_for_update = f"/singlrowupdate" 

    response = requests.post(base_url+api_for_update, json=date_list)

    # Check response
    if response.status_code == 200:
        return redirect(url_for('index'))
    else:
        print("Failed to post data!")
        print(f"Status Code: {response.status_code}, Response: {response.text}")
        return redirect(url_for('index'))
        
        
        
        
    

    
    #return render_template('singlrowview.html', total=total,view_table=view_table,view = VIEWS,welcome = welcome,user_name=user_name, rows=rows, column_names=column_names) 


@app.route('/logout')
def logout():
    session.clear()
    
    # global TableOrView_objs
    # tb0 = 'PSARALIDZE.VIEW_ABOUT'
    # obj_0 = TableOrView_objs[tb0]
    # TableOrView_objs.clear()  # Clear the global object
    # TableOrView_objs[tb0] = obj_0

    flash('You have been logged out...', 'info')

    return redirect(url_for('login'))  
   

@app.route('/GetData', methods=['GET'])
def get_data():
    # URL-დან ცხრილის სახელის მიღება
    table = request.args.get('table')
    fields = request.args.getlist('fields')
    offset = request.args.get('off_set', default=0, type=int)  # default მნიშვნელობა 0
    perpage = request.args.get('per_page', default=1000, type=int)  # default მნიშვნელობა 100

   

    if not table:
       return jsonify({"error": "table not provided"}), 400
    
    ORC = get_db_connection()     
    
    if not fields:
      fields_query = f""" select  COLUMN_NAME
       from PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature f
       where f.view_flag = 1 and  f.table_or_view = upper('{table}') """
      rows,flds = ORC.get_dict_by_dba_select(fields_query)  

      for row in rows:
        fields.append(row[flds[0]])
                                         
    
    #fields.append('offset')  
    #fields.append('perpage')  
    
    if request.method == 'POST':
     filter_params = {key: str(request.form.get(key, "")) for key in fields}
    else:
     filter_params = {key: str(request.args.get(key, "")) for key in fields}
        
    
    filter_string = f' where 1=1 '
    order_string = f' order by 1 desc,2  '

    for key, value in filter_params.items():
        if value:
            if value == "":
             pass  
            elif value == "None":
             filter_string += f" AND g.{key.upper()} is null "
            else:
             filter_string += f" AND g.{key.upper()} like '%{value}%' "  # Adjust case and single quotes for strings
             if key.upper() == 'ID':
                order_string += f" ,{key.upper()} desc "

    # შექმნა SELECT მოთხოვნის სექცია
    select_fields = ', '.join([f'g.{field}' for field in fields])

    # ცხრილიდან მონაცემების წამოღება
    query = f"SELECT rownum, {select_fields} FROM {table} g {filter_string} " 

    # მონაცემების წამოღება და გარდაქმნა JSON ფორმატში
    rows = ORC.get_dict_by_dba_select(query,offset,perpage)[0]
    
    data = rows
   
    #response = json.dumps(data, ensure_ascii=False, indent=4)
    response = jsonify(data)
   

    response.headers['Content-Type'] = 'application/json; charset=utf-8'    
    return response

def get_filter_values(view_table,filter_string,filter_values):    

    OrcUtil = get_db_connection()    
   
    fields_query = f""" 
       select  COLUMN_ID, COLUMN_NAME, FEATURE_ID, NUM_DISTINCT, SAMPLE_SIZE  ,SAMPLE_LIST_JSON,COLUMN_DATA_TYPE,FILTER_FLAG,VIEW_FLAG,ORDERING
       from PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature a 
       where TABLE_OR_VIEW = UPPER('{view_table}') and FEATURE_ID = 1 and FILTER_FLAG = 1 --and  view_flag = 1
       order by COLUMN_ID
    """
    try:
        frows,fcolumns = OrcUtil.get_dict_by_dba_select(fields_query)
    except:
        fcolumns = None
        frows = None  
      
    
    if frows is not None:
        for rw in frows:
           column_name = rw[fcolumns[1]]
           if rw[fcolumns[2]] == 1:  
                query_JSON = f""" SELECT distinct {rw[fcolumns[1]]} FROM {view_table} g {filter_string} order by {column_name} """              
                rw,fld = OrcUtil.get_dict_by_dba_select(query_JSON)
               
            
                list_for_json = []
                for r in rw:
                    list_for_json.append(r[fld[0]])

                filter_values[column_name] = list_for_json    

    return filter_values
    
def get_view_fields(view_table):
    
    OrcUtil = get_db_connection()    
   
    fields_query = f""" 
       select  COLUMN_ID, COLUMN_NAME, FEATURE_ID, NUM_DISTINCT, SAMPLE_SIZE  ,SAMPLE_LIST_JSON,COLUMN_DATA_TYPE,FILTER_FLAG,VIEW_FLAG,ORDERING
       from PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature a 
       where TABLE_OR_VIEW = UPPER('{view_table}') and a.column_data_type not in ('BLOB')
       order by (case when CONSTRAINT_TYPE in ('P','U') then 1 else 0 end) desc, COLUMN_ID
    """
    try:
        frows,fcolumns = OrcUtil.get_dict_by_dba_select(fields_query)
    except:
        fcolumns = None
        frows = None  
        
    
    
    fields = []
    dd_fields = []
    dt_fields = []
    view_filds = [] 
    filter_values = {} 
    
    if frows is None:
        fields_query = f"SELECT * FROM {view_table} g  where rownum < 2"
        rows,fields = OrcUtil.get_dict_by_dba_select(fields_query)
        #dd_fields = fields
    else:
        for rw in frows:
            if rw[fcolumns[8]] == 1:
               view_filds.append(rw[fcolumns[1]])
            if rw[fcolumns[7]] == 1:
                if rw[fcolumns[6]] not in ("TIMESTAMP(6)","DATE"):
                    fields.append(rw[fcolumns[1]])
                if rw[fcolumns[6]] in ("TIMESTAMP(6)","DATE"):
                    dt_fields.append(rw[fcolumns[1]]+"_from")
                    dt_fields.append(rw[fcolumns[1]]+"_to")
                if rw[fcolumns[2]] == 1  and  rw[fcolumns[5]] is not None:  
                    dd_fields.append(rw[fcolumns[1]])    
                    #filter_values[rw[fcolumns[1]]] = json.loads(rw[fcolumns[5]])
                    try:
                      j_date = json.loads(rw[fcolumns[5]])
                      if isinstance(j_date, list):
                        j_date.sort()
                        filter_values[rw[fcolumns[1]]] = j_date
                    except json.JSONDecodeError:
                         filter_values[rw[fcolumns[1]]] = None  


    return fields,dd_fields,filter_values,dt_fields,view_filds

#@app.teardown_appcontext
def close_db_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def build_menu_tree(parent_id=None):
    CC = get_db_connection()
    conn = CC.connection
    cursor = conn.cursor()
    
    # მშობელი ID-ის მიხედვით მენიუს პუნქტების მიღება
    if parent_id is None:
        cursor.execute(f"""SELECT id, name, url, sort_order FROM psaralidze.menu_items WHERE parent_id IS NULL ORDER BY sort_order,name""")
    else:
        cursor.execute(f"""SELECT id, name, url, sort_order FROM psaralidze.menu_items WHERE parent_id = {parent_id} and sort_order > 0 ORDER BY sort_order,name""" )
    
    rows = cursor.fetchall()
    menu = []
    
    for row in rows:
        menu.append({
            "id": row[0],
            "name": row[1],
            "url": row[2],
            "children": build_menu_tree(row[0])  # ქვემენიუს დამატება
        })
    
    #connection.close()
    return menu

@app.route('/', methods=['GET', 'POST'])
def index():

    if 'username' not in session:
        flash('Please log in to access the page.', 'warning')
        session['view_table'] = 'PSARALIDZE.VIEW_ABOUT' 
        return redirect(url_for('login'))  
    
    VIEWS = get_views()
    table = 'PSARALIDZE.VIEW_ABOUT' 
    add_TableOrView_data(table,ORACLE_CONFIG)

    menu_tree = build_menu_tree()
    

    user_name = session["username"]     
    token = session["token"]   
    user_permitions = session['user_permitions']   
    view_table = session.get('view_table', table)
    view_table_changed = session.get('view_table_changed', 1)    

    if request.method == 'GET':  
       view_table = request.args.get("view_table", view_table)
       session['view_table'] = view_table
    
    add_TableOrView_data(view_table,ORACLE_CONFIG)
    view_tables = list(TableOrView_objs.keys()) 
 
    
    filter_f = []
    view_f = []
    if len(view_tables) > 0:
        view_values = TableOrView_objs[view_tables[len(view_tables)-1]].fields
        for f in view_values:
           if f[5] == 1:
            filter_f.append(f[1])      
           if f[6] == 1:
            view_f.append(f[1])       
           
          
    else:
        view_values = None
        filter_f = None

    

    if view_table in VIEWS:
       table = view_table   
    
    page = request.form.get("page", 1, type=int)    
    per_page = 20                   
    offset = (page - 1) * per_page      
   
    welcome = f"view_table = {view_table}"  
    session['view_table_changed'] = 0    
    
    OrcUtil = get_db_connection()    

    fields,dd_fields,filter_values,dt_fields,view_filds = get_view_fields(table)   
    
    
    filter_params = {}    

    fields = fields + dt_fields
    
    if request.method == 'POST':       
     filter_params = {key: str(request.form. get(key, "")) for key in fields}
    else:
     filter_params = {key: str(request.args.get(key, "")) for key in fields}

   
    api_filter_values = "" 
    filter_string = f' where 1=1 '
    order_string = f' order by 1 desc,2  '

    

    for key, value in filter_params.items():
        if value:
            if key in dt_fields: 
               if "_from" in key:
                    filter_string = filter_string + f" and " + key.replace('_from', '') + " >= date'" + value + "'"
               else:
                    filter_string = filter_string + f" and " + key.replace('_to', '') + " < date'" + value + "' + 1 "
            else:
                if value == "":
                 api_filter_values = api_filter_values + f"&{key.upper()}="  
                elif value == "None":
                 filter_string += f" AND g.{key.upper()} is null "
                else:
                 filter_string += f" AND g.{key.upper()} like '%{value}%' "  # Adjust case and single quotes for strings
                 api_filter_values = api_filter_values + f"&{key.upper()}={value}" 
                if key.upper() == 'ID':
                    order_string += f" ,{value} desc "
    
    
    # შექმნა SELECT მოთხოვნის სექცია  view_filds dan 
    select_fields = ', '.join([f'g.{field}' for field in view_filds ])  #if field not in dt_fields

    
    
    
    query_total = f"SELECT count(*) CC FROM {table} g {filter_string}"
    rc,c = OrcUtil.get_dict_by_dba_select(query_total)
    total = len(c)    
    total = rc[0]['CC']

    #welcome = welcome + f"... total = {total} ... offset = {offset} "   
    rows = None    
    # Main query to fetch data
    query = f"SELECT {select_fields} FROM {table} g {filter_string} "    
    rows, column_names = OrcUtil.get_dict_by_dba_select(query,offset,per_page)

    if rows == None:
       query = f"SELECT {select_fields} FROM {table} g rownum < 2 "    
       rows, column_names = OrcUtil.get_dict_by_dba_select(query,offset,per_page)
    
    if total < 2000 and total > 1:
       filter_values = get_filter_values(view_table,filter_string,filter_values)       
 
    
    #permision = 'PLANNER_ADMIN'
    permissions = eval(CONFIG.get_value('permissions','permissions_v_0'))
    
    if all(perm not in user_permitions for perm in permissions):
       welcome = f" N/A permision : {permissions} in : {user_permitions}"
       rows = None    

    api_filter_values = api_filter_values.replace("%27", "")
    
    
    if column_names:
      alias_dict = json.loads(get_alias_dict())
      columns_alias = get_columns_alias(column_names,alias_dict)  
    else:
      columns_alias = column_names
    welcome = f"... სულ მოიძენა {total} ჩანაწერი ..."    
    #welcome = f"... filter_params = {filter_params}  " 
    #welcome = f"... filter_values = {filter_values}  "  
    #welcome = f"... query = {query}  ............. ... filter_params = {filter_params} "    
    #welcome = f"... alias_dict : {alias_dict}  ...columns_alias : {columns_alias}"    
    #menu_tree=menu_tree,
    
    if view_table=='PSARALIDZE.VIEW_ABOUT':
        return render_template('about.html', filter_f=filter_f,view_values=view_values,view_tables=view_tables,menu_tree=menu_tree,columns_alias=columns_alias,dt_fields=dt_fields,api_filter_values=api_filter_values,view_table=view_table, view_table_changed=view_table_changed, offset=offset, page=page, total=total, per_page=per_page, view = VIEWS,user_name=user_name,query=query,welcome = welcome, column_names=column_names, rows=rows, filter_params=filter_params, filter_values=filter_values,dd_filter_fields = dd_fields, filter_fields=fields)
    else:
        if total == 1:
            return render_template('singlrowview.html', menu_tree=menu_tree,columns_alias=columns_alias,dt_fields=dt_fields,api_filter_values=api_filter_values,view_table=view_table, view_table_changed=view_table_changed, offset=offset, page=page, total=total, per_page=per_page, view = VIEWS,user_name=user_name,query=query,welcome = welcome, column_names=column_names, rows=rows, filter_params=filter_params, filter_values=filter_values,dd_filter_fields = dd_fields, filter_fields=fields)
        else:
            return render_template('index.html', menu_tree=menu_tree,columns_alias=columns_alias,dt_fields=dt_fields,api_filter_values=api_filter_values,view_table=view_table, view_table_changed=view_table_changed, offset=offset, page=page, total=total, per_page=per_page, view = VIEWS,user_name=user_name,query=query,welcome = welcome, column_names=column_names, rows=rows, filter_params=filter_params, filter_values=filter_values,dd_filter_fields = dd_fields, filter_fields=fields)
    
@app.errorhandler(403)
def forbidden(e):

    app.secret_key = os.getenv('SECRET_KEY', 'default_fallback_key')
    return f"<h1>403 {app.secret_key} Forbidden</h1><p>თქვენ არ გაქვთ წვდომა ამ რესურსზე.</p>", 403

@app.route('/download', methods=['GET', 'POST'])
def download():
   
    OI_EXEL = get_db_connection()  
    
    
    if request == "GET":
       query_exel = request.args.get("query","select 'N/A' query from dual ")   
    else: 
       query_exel = request.form.get("query", "select 'N/A' query from dual")

    exel_data = OI_EXEL.get_exel_data(f"""{query_exel}""")    

    # Pandas DataFrame-ი ქმნის CSV

    import pandas as pd 
    import datetime 
    from io import BytesIO

    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y%m%d_%H%M%S")

    df = pd.DataFrame(exel_data)
    
    # Create a BytesIO buffer
    output = BytesIO()

    # Save the DataFrame to the buffer in Excel format
    df.to_excel(output, index=False, engine='openpyxl')

    # Seek to the beginning of the stream
    output.seek(0)

    # Create a response with the buffer content
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={session["view_table"]+'_'+formatted_time}_data.xlsx'
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    return response

@app.route('/process_data', methods=['POST'])
def process_data():
    # მიღებული მონაცემების ამოღება
    data = request.get_json()  # AJAX-ში JSON ფორმატში ვაგზავნით მონაცემებს
    
    # მონაცემების დამუშავება
    table = data.get('table')
    off_set =  data.get('off_set')
    per_page =  data.get('per_page')    
    
    # შედეგის დაბრუნება
    response = {
        'status': 'success',
        'message': f"Received data: table - {table}, per_page - {per_page}, off_set - {off_set}"
    }
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, host='192.168.54.11', port=8080)
