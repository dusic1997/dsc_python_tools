import json
import re
import sys

from pypinyin import lazy_pinyin, Style

# Access command-line arguments
arguments = sys.argv
# Specify the path to your JSON file
json_file_path = arguments[1]

# Open and read the JSON file
with open(json_file_path, 'r') as json_file:
    # Load the JSON data into a Python dictionary
    data = json.load(json_file)

def generate_dart_class(class_name, swagger_json):
    dart_class = []

    # Begin the Dart class definition with the provided class name
    for line in swagger_json.get("description", "").split("\n"):
        dart_class.append(f"///{line}")
    dart_class.append(f"class {class_name} {{")

    # Parse the "properties" field of the Swagger JSON
    properties = swagger_json.get("properties", {})
    if  len(properties.items())==0:
        return f"class {class_name}" + '{  Map<String, dynamic> toJson() =>{};    '+ f'{class_name}.fromJson(Map<String, dynamic> json) '+ '{}  }\n\n'
    for prop_name, prop_info in properties.items():
        prop_info['prop_name_pinyin']=''
        if re.findall(r'[\u4e00-\u9fa5]',prop_name):
            prop_name_pinyin = ''.join(lazy_pinyin(prop_name, style=Style.TONE3))
            prop_name_pinyin = re.sub(r'[^a-zA-Z0-9_]', '', prop_name_pinyin)
            prop_info['prop_name_pinyin']=prop_name_pinyin
        prop_type = prop_info.get("type", "dynamic")
        prop_format = prop_info.get("format", "")
        prop_description = prop_info.get("description", "")
        prop_ref = prop_info.get("$ref", "").replace("#/components/schemas/", "")
        prop_list_type = prop_info.get("items", {}).get("$ref", "").replace("#/components/schemas/", "")
        prop_desc = prop_info.get("description", "")
        # Check if the property type is "integer" and format is "int64" or "int32"
        if prop_type == "integer":
            if prop_format == "int64":
                prop_type = "String"  # Change the type to String for int64
            elif prop_format == "int32":
                prop_type = "int"  # Change the type to int for int32
        elif prop_type=="number":
            prop_type = "double"
        elif prop_type=="string":
            prop_type = "String"
        elif prop_type=="array":
            prop_type = "List"
            if prop_list_type!="":
                prop_type = f"List<{prop_list_type}>"
        elif prop_type=="boolean":
            prop_type = "bool"
        elif prop_type=="object":
            prop_type = "dynamic"
        elif prop_ref!="":
            prop_type = prop_ref
        prop_info["prop_type"]=f"{prop_type}?"
        prop_info['prop_list_type']=prop_list_type
        # Define the Dart property
        for line in prop_desc.split("\n"):
            dart_class.append(f"  ///{line}")
        if prop_info['prop_name_pinyin']=='':
            dart_class.append(f"  {prop_type}? {prop_name};")
        else:
            dart_class.append(f"  {prop_type}? {prop_info['prop_name_pinyin']};")
    # Create the Dart class constructor
    dart_class.append(f"\n  {class_name}({{")
    for prop_name,prop_info in properties.items():
        if prop_info['prop_name_pinyin']=='':
            dart_class.append(f"    this.{prop_name},")
        else:
            dart_class.append(f"    this.{ prop_info['prop_name_pinyin']},")
            
    dart_class.append("  });\n")

    # Create the Dart class JSON deserialization constructor
    dart_class.append(f"  {class_name}.fromJson(Map<String, dynamic> json) {{")
    for prop_name,prop_info in properties.items():
        prop_name_legal = prop_name
        if prop_info['prop_name_pinyin']!='':
            prop_name_legal = prop_info['prop_name_pinyin']
        if prop_info['prop_list_type']!='':
            prop_list_type = prop_info['prop_list_type']
            dart_class.append(f"    {prop_name_legal} = json['{prop_name}']?.map<{prop_list_type}>((x) => {prop_list_type}.fromJson(Map<String, dynamic>.from(x))).toList();")
        
                
        elif prop_info['prop_type'].replace('?','') not in ["int","String","double","bool","dynamic",'List']:
            
            dart_class.append(f"    {prop_name_legal} = {prop_info['prop_type'].replace('?','')}.fromJson(Map<String, dynamic>.from(json['{prop_name}']));")
        else:
            dart_class.append(f"    {prop_name_legal} = json['{prop_name}'] ;")
    dart_class.append("  }\n")

    # Create the Dart class JSON serialization method
    dart_class.append("  Map<String, dynamic> toJson() {")
    dart_class.append("    final Map<String, dynamic> jsonData = {};")
    for prop_name,prop_info in properties.items():
        prop_name_legal = prop_name
        if prop_info['prop_name_pinyin']!='':
            prop_name_legal = prop_info['prop_name_pinyin']
        if prop_info['prop_list_type']!='':
            dart_class.append(f"    jsonData['{prop_name}'] = {prop_name_legal}?.map((x)=>x.toJson()).toList();")
        elif prop_info['prop_type'].replace('?','') not in ["int","String","double","bool","dynamic",'List']:
            dart_class.append(f"    jsonData['{prop_name}'] = {prop_name_legal}?.toJson();")
        else:    
            dart_class.append(f"    jsonData['{prop_name}'] = {prop_name_legal};")
    dart_class.append("    return jsonData;")
    dart_class.append("  }")

    # Close the Dart class definition
    dart_class.append("}")

    return "\n".join(dart_class)+'\n\n'




code = '''
import 'package:dio/dio.dart';

final dio  = Dio();
const baseUrl = '';
'''
# Generate Dart class
for class_name,swagger_json in data['components']['schemas'].items():
    dart_code = generate_dart_class(class_name, swagger_json)
    code +=dart_code
    
    
api_client_class = 'class ApiClient {\n' 
methods = []  
for path,swagger_json in data['paths'].items():
    if not isinstance(swagger_json,dict):
        continue
    function_name = path.replace('/','_').replace('{','_').replace('}','_').replace('-','_')
    for method,info in swagger_json.items():
        desc = info.get('description',"").replace('\n',' ')
        try:
            return_type = info['responses']['200']['content']['*/*']['schema']['$ref'].replace('#/components/schemas/','')
        except:
            return_type = 'dynamic'
        params = ','.join(p['name'] for p in info.get('parameters',[]))
        dart_code =f'///{info.get("description","")}\n'
        for param in info.get('parameters',[]):
            if param['in'] == 'query':
                dart_code += '/// '+param['name']+':' +param.get("description","")+';\n'
        request_body_type = info.get('requestBody',{}).get('content',{}).get('application/json',{}).get('schema',{}).get('$ref',"").replace("#/components/schemas/","")
        
        dart_code  +=f'\nstatic Future<{return_type}> {method}_{function_name}('
        if params+request_body_type!=''  :
            dart_code +='{'
        dart_code +=params
        if request_body_type!='':
            if params!='':
                  dart_code += ','
            dart_code += f'required {request_body_type} data'
        if params+request_body_type!=''   :
            dart_code +='}'
        dart_code +=')async{\n'
        dart_code +=f'var resp =await dio.{method}(baseUrl+"{path.replace("{","${")}",queryParameters:'
        
        dart_code +='{'
        for param in info.get('parameters',[]):
            if param['in']=='query':
                
                dart_code += f'"{param["name"]}":{param["name"]},'
       
        dart_code +='} '
        if  request_body_type!='' :
            dart_code +=f',data:data.toJson()'   
        dart_code +=');\n'
        dart_code +=f'return {return_type}.fromJson(resp.data);'
        dart_code+='\n}\n'
        """"""
    api_client_class += dart_code
    
api_client_class +='}'   

code += api_client_class   
with open(f"{json_file_path}.dart", "w") as f:
        # print(dart_code)
        f.write(code)        
