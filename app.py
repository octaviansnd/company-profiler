from flask import Flask, request, jsonify
from algoliasearch.search_client import SearchClient

app = Flask(__name__)

# Algolia client
client = SearchClient.create('WWY1GU3B3V', 'e138cba99e91f6ee78651488c19d7ba6')
index = client.init_index('dev_companyprofile')

@app.route('/', methods=['GET'])
def search_company():
    try:
        name = request.args.get('name', '')
        website = request.args.get('website', '')
        phone_number = request.args.get('phone_number', '')
        facebook_profile = request.args.get('facebook_profile', '')

        query = " ".join([name, website, phone_number, facebook_profile])
        result = index.search(query)

        # Return the best matching company profile
        if result['hits']:
            return jsonify(result['hits'][0])
        else:
            return jsonify({'message': 'Company profile not found'}), 404
    except Exception as e:
        print('Error:', e)
        return jsonify({'message': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)
