import re
import requests
import json
import sys
import os

TEMPLATE = '''
{{api_path}}
--------------
**Method**: `{{request_method}}`


# Request

|     Parameter       |      Type       |   Required   |
|---------------------|:---------------:|--------------|
{{request_params}}


# Response

{{response_params}}

## Example

````
{{request_type}} {{url}}

{{example_request}}
````
'''

class TemplateHelper:
	doc_template = TEMPLATE
	out = []


	@classmethod
	def extract_keys(cls, dict_in):
		if isinstance(dict_in, unicode):
			cls.out.append(dict_in)
		else:
			for key, value in dict_in.items():
				if isinstance(value, dict): # If value itself is dictionary
					cls.extract_keys(value)
				elif isinstance(value, list):
					if value:
						for item in value:
							cls.extract_keys(item)
				elif isinstance(value, unicode):
					cls.out.append(key)

		return cls.out

	@classmethod
	def update_header(cls, api_path, request_method):
		api_path = re.search(r'/api/default/v1/([^?]+)', api_path).group(1)
		for arg, value in locals().items():
			cls.doc_template = str(cls.doc_template).replace('{{' + str(arg) + '}}', str(value))

	@classmethod
	def update_request(cls, method_type, url, raw_data):
		request_temp_line = '| {{param}}            | `string`        | Yes          |'
		params = None
		get_params = ''
		
		if method_type == 'GET':
			get_params = re.sub(r'.*\?', '?', url)
			params = re.findall(r'(?<=[?&])\w+', get_params)

		else:
			if raw_data:
				params = cls.extract_keys(json.loads(raw_data))
				cls.out = []

		if params:
			request_params = '\n'.join([request_temp_line.replace('{{param}}', param) for param in params])
			cls.doc_template = str(cls.doc_template).replace('{{request_params}}', request_params)

	@classmethod
	def update_response(cls, response):
		header_lines = ['|     Parameter       |      Type       |   Required   |',
                         '|---------------------|:---------------:|--------------|']
		response_temp_line = '| {{param}}            | `string`        | Yes          |'
		if response:
			if response['text']:
				params =  cls.extract_keys(json.loads(response['text']))
				cls.out = []
				if params:
					res_params = '\n'.join(header_lines) + '\n' + '\n'.join([response_temp_line.replace('{{param}}', param) for param in params])
					cls.doc_template =  str(cls.doc_template).replace('{{response_params}}', res_params)

	@classmethod
	def update_example(cls, method_type, url, raw_data, response=None):
		cls.doc_template = str(cls.doc_template).replace('{{url}}', url)
		if method_type == 'GET':
			cls.doc_template = str(cls.doc_template).replace('{{request_type}}', 'GET')
		else:
			cls.doc_template = str(cls.doc_template).replace('{{request_type}}', 'POST')
		if response:
			data = response['text']
			if raw_data:
				data = '**Request:**\n{}\n**Response**\n{}'.format(raw_data, data)
			cls.doc_template = str(cls.doc_template).replace('{{example_request}}', data)

	@classmethod
	def write_file(cls, file_name):
		with open(file_name, 'w') as f:
		    f.write(str(cls.doc_template))
		    print 'Write completed on '+ file_name


	@classmethod
	def reset_template(cls):
		cls.doc_template = TEMPLATE


def main():
	if len(sys.argv) < 2:
		raise Exception('''\033[92mYou must pass the postman collections url as argument. 
			Ex: python script.py url\33[0m''')

	# Get the url
	url = sys.argv[1]
	base_dir = os.path.dirname(os.path.abspath(__file__))

	# Get the data
	r = requests.get(url)
	if r.status_code != 200:
		raise Exception('''\033[92mPlease check your internet connection.\33[0m''')

	data = json.loads(r.content)
	folders = data["folders"]

	folders_tuple = [(i['id'], i['name']) for i in folders]
	folders_dict = dict(folders_tuple)

	folder_names = folders_dict.values()
		

	# Check whether the directory exists or not. If not create a one.
	if folder_names:
		for fol in folder_names:
			new_folder = base_dir + os.sep + fol
			path = os.path.exists(new_folder)
			if not path:
				os.makedirs(new_folder)
	else:
		folder_names = [base_dir]

	#iterate over the requests
	json_requests = data['requests']
	for request in json_requests:
		folder_id = request.get('folder', None)
		folder_name = None
		if folder_id:
			folder_name = folders_dict.get(folder_id, None)

		url = request['url']
		req_method = request['method']
		raw_data = request.get('rawModeData', None)
		folder_na, api_path = re.search(r'/api/default/v1/'+'(\w+)/' + '([^?]+)', url).groups()
		if not folder_name:
			for j in folder_names:
			    if folder_na[0].upper() + folder_na[1:] in j:
			    	folder_name = j
			    	break
		if not folder_name:
			folder_name = folder_names[0]

		file_name = '_'.join(api_path.split('/')) + '.md'

		# Modify the template
		TemplateHelper.update_header(url, req_method)
		TemplateHelper.update_request(req_method, url, raw_data)
		responses = request.get('responses', None)

		if responses:
			TemplateHelper.update_response(responses[-1])
			TemplateHelper.update_example(req_method, url, raw_data, responses[-1])
		TemplateHelper.update_example(req_method, url, raw_data)

		# check whether the file exists for not
		#is_file_exists = os.path.exists(os.path.join(base_dir , folder_name , file_name))

		TemplateHelper.write_file(os.path.join(base_dir, folder_name , file_name))

		TemplateHelper.reset_template()


if __name__ == "__main__":

	main()
