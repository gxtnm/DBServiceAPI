import cx_Oracle
import pandas as pd
import os
import json
import base64

class OracleUtils():

    def __init__(self, username, password, host, port, service_name):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.service_name = service_name
        self.dsn = cx_Oracle.makedsn(self.host, self.port, service_name=self.service_name)
        self.column_types = None   
        self.connection =  cx_Oracle.connect(user=self.username, password=self.password, dsn=self.dsn)
                    


    def get_dict_by_dba_select(self, query,offset = 0,per_page = 100):
        records = [] 
        try:            
            cursor = self.connection.cursor() 
            cursor.execute(query + f' OFFSET {offset} ROWS FETCH NEXT {per_page} ROWS ONLY')
            rows = cursor.fetchall()
            if not rows:  # თუ rows არის ცარიელი
                #print("No data returned : " + query + "\n")
                return None,None  # ვაბრუნებთ None
                    
            column_names = [col[0] for col in cursor.description]
            self.column_types = [col[1] for col in cursor.description]
            # records = [dict(zip(column_names, row)) for row in rows]                    
            for row in rows:
                record = {}
                for col_name, col_value in zip(column_names, row):
                    if isinstance(col_value, cx_Oracle.LOB):  # თუ სვეტის ტიპი LOB-ია
                        record[col_name] = col_value.read()  # LOB-ის წაკითხვა
                    else:
                        record[col_name] = col_value # სხვა სვეტების ჩვეულებრივი ჩანაწერი
                records.append(record)
        except cx_Oracle.DatabaseError as e:
            print(f"query = {query} : Database error: {e}")
            records = []
            column_names = []
       
        
        return records, column_names
    
    def get_rows_by_dba_select(self, query,offset = 0,per_page = 100):
        records = [] 
        try:            
            cursor = self.connection.cursor() 
            cursor.execute(query + f' OFFSET {offset} ROWS FETCH NEXT {per_page} ROWS ONLY')
            rows = cursor.fetchall()
            if not rows:  # თუ rows არის ცარიელი
                #print("No data returned : " + query + "\n")
                return None,None  # ვაბრუნებთ None
                    
            column_names = [col[0] for col in cursor.description]
            self.column_types = [col[1] for col in cursor.description]
            # records = [dict(zip(column_names, row)) for row in rows]                                      
            for row in rows:     
                record = []                     
                for ii in range(len(row)):
                    if isinstance(row[ii], cx_Oracle.LOB):  # თუ სვეტის ტიპი LOB-ია
                        #record.append(base64.b64encode(row[ii].read()))  # BLOB-ის წაკითხვა  base64.b64encode(col_value.read())
                        record.append(row[ii].read())   # CLOB-ის წაკითხვა
                    else:
                        record.append(row[ii]) # სხვა სვეტების ჩვეულებრივი ჩანაწერი
                    records.append(record)
        except cx_Oracle.DatabaseError as e:
            print(f"Database error: {e}")
            records = []
            column_names = []
       
        
        return records, column_names
    
    def dba_insert_update_query(self, update_query):  
        try:            
            cursor = self.connection.cursor() 
            cursor.execute(update_query)
            rowcount = cursor.rowcount  # რამდენი რიგი განახლდა

            if rowcount == 1:
                self.connection.commit()  # მხოლოდ მაშინ ვაკეთებთ commit, თუ განახლდა ერთი რიგი
                #print(f'insert_update -- {update_query} -- successful for 1 row')
            else:
                self.connection.rollback()  # თუ მეტი ან ნაკლები რიგი განახლდა, ვაკეთებთ rollback-ს
                #print(f"Update failed. {rowcount} rows were affected. Rolling back.")
        except cx_Oracle.DatabaseError as e:
            print(f"insert_update -- {update_query} -- error : {e}")
            return False
            #exit(0)
        return True

    def  create_table_from_data(self,data_file):
        
        file_name, file_extension = os.path.splitext(data_file)
        print(f'file_extension = {file_extension}')
        
        table_name = os.path.splitext(os.path.basename(data_file))[0]

        print(f'table_name = {table_name}')

        if file_extension == '.xlsx':
             df = pd.read_excel(data_file)
             if df.empty:
               return
             #print(df)
        
        create_query = f'create table {table_name} as select '
        insert_query = f'insert into {table_name} select '

        for index, row in df.iterrows():
            print(f"Index:", index)  # სტრიქონის ინდექსი ...
            #print("Row type:" + type(row))   
            if  index == 0:
                insert_query = create_query + " CAST(' "+ str(index) +"' AS VARCHAR2(4000))  indx "      # CAST('0' AS VARCHAR2(4000)) 
            else:
                insert_query = insert_query + " CAST(' "+ str(index) +"' AS VARCHAR2(4000))  indx "         
            
            for column in df.columns:
                vl = row[column]
                if isinstance(vl, pd.Timestamp):
                   vl = vl.strftime('%Y-%m-%d')
                if pd.isnull(vl):
                   vl = 'null'                
                insert_query = insert_query + f"  , CAST('{str(vl)} ' AS VARCHAR2(4000))   {str(column)} "            
            insert_query += ' from dual '
            if  index == 0:
                self.dba_table_change_query(insert_query)                       
            else:
                self.dba_insert_update_query(insert_query)                  
            insert_query = f'insert into {table_name} select '

            return True
        
        
    def dba_table_change_query(self, query):
        try:            
            cursor = self.connection.cursor() 
            cursor.execute(query)
            #print(f"Table change : {query} executed successfully.")
        except cx_Oracle.DatabaseError as e:
            print(f"Database error: {e}")
            return False

        return True

    def get_exel_data(self, query):
        
        data = {}

        records = [] 
        try:            
            cursor = self.connection.cursor() 
            cursor.execute(query)
            rows = cursor.fetchmany(200000) 
            if not rows:  # თუ rows არის ცარიელი
                #print("No data returned : " + query + "\n")
                return None,None  # ვაბრუნებთ None
                    
            column_names = [col[0] for col in cursor.description]
            self.column_types = [col[1] for col in cursor.description]
            # records = [dict(zip(column_names, row)) for row in rows]                    
            for row in rows:
                record = {}
                for col_name, col_value in zip(column_names, row):
                    if isinstance(col_value, cx_Oracle.LOB):  # თუ სვეტის ტიპი LOB-ია
                        record[col_name] = col_value.read()  # LOB-ის წაკითხვა
                    else:
                        record[col_name] = col_value  # სხვა სვეტების ჩვეულებრივი ჩანაწერი
                    records.append(record)
        except cx_Oracle.DatabaseError as e:
            print(f"Database error: {e}")
            records = []
            column_names = []
        
        for c in column_names:
            data[c] = []

        for r in records:
            for c in column_names:
                data[c].append(r[c]) 
        
        return data      
    
    def write_json_in_oracle(self, json_data, table, column):

        clear_query = f"""
            UPDATE PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature
            SET SAMPLE_LIST_JSON = TO_CLOB('')
            WHERE COLUMN_NAME = upper('{column}')
            AND TABLE_OR_VIEW = upper('{table}')
            """ 
        self.dba_insert_update_query(clear_query)
        
        chunk_size = 2000
        
        if isinstance(json_data, dict) or isinstance(json_data, list):
            json_string = json.dumps(json_data)

        else:
            json_string = json_data

        json_chunks = [json_string[i:i + chunk_size] for i in range(0, len(json_string), chunk_size)]
    
            
        for chunk in json_chunks:  
            
            chunk_query = f"""
            UPDATE PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature
            SET SAMPLE_LIST_JSON = nvl(SAMPLE_LIST_JSON,'') || TO_CLOB('{chunk}')
            WHERE COLUMN_NAME = upper('{column}')
            AND TABLE_OR_VIEW = upper('{table}')
            """ 
            self.dba_insert_update_query(chunk_query)
        print(chunk_query)

       

        
        