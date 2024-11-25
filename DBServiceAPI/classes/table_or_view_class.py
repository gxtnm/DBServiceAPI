from Dir_MyClasses.oracle_class import OracleUtils

class TableOrView:
    def __init__(self,name,ORACLE_CONFIG):
        self.name =  name
        self.fields = None
        self.field_keys = None        
        self.set_name(name,ORACLE_CONFIG)
        
        
    def set_name(self,owner_table,ORACLE_CONFIG):

        self.name = owner_table

        TBW_OU = OracleUtils(ORACLE_CONFIG['username'],ORACLE_CONFIG['password'],ORACLE_CONFIG['host'],ORACLE_CONFIG['port'],ORACLE_CONFIG['service_name'])
        
        query = f"""    select 
                         COLUMN_ID
                        ,COLUMN_NAME
                        ,COLUMN_ALIAS
                        ,ORDERING,FEATURE_ID
                        ,FILTER_FLAG
                        ,VIEW_FLAG
                        ,CONSTRAINT_TYPE
                        ,COLUMN_DATA_TYPE
                        ,NUM_DISTINCT
                        ,SAMPLE_SIZE
                        ,SAMPLE_LIST_JSON
                        ,COLUMN_UNIQ_ID
                        from PSARALIDZE.TABLE_OR_VIEW_COLUMN_feature f 
                        WHERE table_or_view = upper('{owner_table}') order by (case when CONSTRAINT_TYPE  in ('P','U')  then 1 else 0 end) desc,COLUMN_ID """      
        
        
        self.fields, self.field_keys = TBW_OU.get_rows_by_dba_select(query,0,10000)

        
    