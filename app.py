'''
File app.py

Created following input from Copilot for Flask App
'''

import os
import re
import json
from datetime import datetime

from flask import Flask, request, jsonify, render_template, g
from rank_bm25 import BM25Okapi  # Assuming you use BM25 for retrieval

app = Flask(__name__)

DATA_FOLDER = 'Information' #not using full path now as app is in location
PENDING = 'pending_content' #ditto

#load the JSON documents in memory
def load_documents():
    documents = []
    for filename in os.listdir(DATA_FOLDER):
        #print('Processing File: ',filename)
        if filename.endswith(".json"):
            with open(os.path.join(DATA_FOLDER,filename),'r',encoding="utf-8") as file:
                documents.append(json.load(file))
            #print('Processed : ',filename)
    return documents

#preprocess for BM25
def preprocess_data(doc):
    content = doc['title'] + doc['summary'] + doc['content']
    return content.lower().split()

#Search for an input query and return matching documents.
#This is handled by Ajax and so we do not have a render template
def search_documents(query):
    query_tokens = query.lower().split()
    scores = bm25.get_scores(query_tokens)
    #now rank
    ranked_results = sorted(zip(all_documents,scores),
                            key=lambda x: x[1],reverse=True)

    #optional - add a search in the tags field iff one query_token
    if len(query_tokens) > 1:
        #retrun top n
        return [doc for doc,score in ranked_results if score > 0]
    
    tag_match = []
    for doc in all_documents:
        #print(doc['tags'])
        tags = [t.lower() for t in doc['tags']]
        if query_tokens[0] in tags:
            tag_match.append(doc)
    #tag_match = [doc for doc in all_documents if any(query_tokens in tag.lower() for tag in doc['tags'])]
    #print(tag_match)
    #print(ranked_results)
    #combine rank and tag
    final_results = tag_match + list({doc['title']: doc for doc, _ in ranked_results}.values()) + tag_match    
    
    return final_results#[:3]

#Clean up the content from non-print characters before saving
def clean_text(text):
    """Removes non-printable characters and unnecessary whitespace"""
    text = re.sub(r"[^\x20-\x7E]", "", text)  # Keeps only printable ASCII characters
    text = re.sub(r"\s+", " ", text).strip()  # Removes extra spaces/newlines
    return text

#Add a new document, if get then show the empty text boxes, and if post
#collect user's input and save in pending location
@app.route("/add_document",methods=["GET","POST"])
def handle_add_document():
    if request.method == "GET":
        return render_template('create_document.html')
    
    data = request.json #Receive data from front end
    
    # Clean user input before saving
    cleaned_content = clean_text(data["content"])
    cleaned_res = [clean_text(entity) for entity in data['resources']]
    print(cleaned_res)
    new_doc = {
        'title' : clean_text(data['title']),
        'summary' : clean_text(data['summary']),
        'content' : cleaned_content,
        'tags': [clean_text(tag) for tag in data['tags']],
        'resources': [{'url':res.split(';')[0],
                       'name':res.split(';')[1]}
                      for res in cleaned_res],
        "last_updated": "Today"
        }
    #Now save the data actually. File name should be entry of first tag
    #if it is multi word, then join them by _
    save_name = '_'.join(new_doc['tags'][0].split())+'.json'
    #new_doc = json.dumps(new_doc)
    with open(PENDING+'/'+save_name,'w+') as fp:
        json.dump(new_doc,fp,indent=4)

    '''
    # Dummy dataset for demonstration
    all_documents = load_documents()

    tokenized_docs = [preprocess_data(doc) for doc in all_documents]
    bm25 = BM25Okapi(tokenized_docs)
    '''
    return jsonify({"message":"Document added successfully","document":new_doc})

#Go to Home Page which shows a search box
@app.route("/")
def home():
    return render_template("index.html")

#After one of the search results are clicked, you get the clicked one's name as doc_id from javascript
#so check for all_documents and see whose title you got and show that
#alternatively, you may read again and show as well, but this one is cheaper
@app.route("/document/<doc_id>")
def view_document(doc_id):
    print(doc_id)
    my_doc = next((doc for doc in all_documents if doc['title'].lower().replace(" ","-") == doc_id ),None)
    my_doc['name'] = my_doc['tags'][0]
    print(my_doc['tags'])
    print(my_doc['resources'])
    if my_doc:
        return render_template("show_document.html",document = my_doc)
    else:
        return 'Clicked Document Not Found',404

#<strong>${result.title}</strong> <br>${result.summary} <br>	
#<a href="${result.resources[0].url}" target="_blank">Learn More</a>
#via jasonify, so that ajax can show that
#Once user sends a search query, call the search documents function and return the results
@app.route("/search", methods=["POST"])
def search():
    data = request.json
    query = data['query']#request.json.get("query", "")
    results = search_documents(query)
    
    return jsonify({"results": results})

#Show the documents yet to be merged, specifically json files at pending directory
@app.route("/pending_documents")#, methods=["GET"])
def show_pending_documents():
    pending_files = os.listdir(PENDING)
    
    if not pending_files:  # If no files exist, show "No backlog"
        return render_template("pending_documents.html", documents=[], no_backlog=True)

    pending_docs = []
    for filename in pending_files:
        with open(os.path.join(PENDING, filename), "r") as fp:
            doc = json.load(fp)
            if 'edit_' in filename:
                doc['status'] = 'edit'
            else:
                doc['status'] = 'new'
            pending_docs.append({"name": filename, "title": doc["title"], "status":doc["status"]})
    
    return render_template("pending_documents.html", documents=pending_docs, no_backlog=False)

#Review one of the pending documents. It will show the submitted content
@app.route("/review_document/<doc_name>")
def review_document(doc_name):
    pending_file = "{}/{}".format(PENDING,doc_name)
    
    if os.path.exists(pending_file):
        with open(pending_file,"r") as fp:
            doc = json.load(fp)
        doc['name'] = doc_name
        print(type(doc))
        return render_template("review_document.html",document=doc)

    return "Document NOT Found",404

#Try editing an existing document. Clicking edit will open the content in editable text boxes
@app.route("/edit_document/<doc_name>")
def edit_document(doc_name):
    approved_file = "{}/{}.json".format(DATA_FOLDER,doc_name)
    
    if os.path.exists(approved_file):
        with open(approved_file, "r") as f:
            doc = json.load(f)

        doc['tags'] = ','.join(doc['tags'])
        doc['name'] = doc_name
        
        return render_template("edit_document.html", document=doc)

    return "Document not found YOU JACKASS", 404  # This should NOT redirect to home!

#Approve a submitted document. On approval the content moves to information folder from the pending folder
@app.route("/approve_document/<doc_name>", methods=["POST"])
def approve_document(doc_name):
    pending_file = "{}/{}".format(PENDING,doc_name)
    approved_file = "{}/{}".format(DATA_FOLDER,doc_name)
    print(data["tags"])
    print(data["resources"])

    if os.path.exists(pending_file):
        with open(pending_file, "r") as fp:
            doc = json.load(fp)

        data = request.json
        doc["title"] = data["title"]
        doc["summary"] = data["summary"]
        doc["content"] = data["content"]
        doc["tags"] = data["tags"]
        doc["resources"] = data["resources"]

        with open(approved_file, "w+") as fp:
            json.dump(doc, fp, indent=4)

        os.remove(pending_file)  # Remove from pending list
        all_documents = load_documents()
        tokenized_docs = [preprocess_data(doc) for doc in all_documents]
        bm25 = BM25Okapi(tokenized_docs)

        return jsonify({"message": "Document approved and indexed!"})

    return jsonify({"error": "Document not found"}), 404

#Reject a preview document. On clicking reject the document gets deleted from Pending folder
@app.route("/reject_document/<doc_name>", methods=["POST"])
def reject_document(doc_name):
    pending_file = "{}/{}".format(PENDING,doc_name)
    print(pending_file)
    if os.path.exists(pending_file):
        os.remove(pending_file)  # Delete the rejected file
        return jsonify({"message": "Document rejected and removed!"})

    return jsonify({"error": "Document not found."}), 404

#Post edit put the new version in pending but do not remove the original, as this needs a review process
@app.route("/submit_edit/<doc_name>", methods=["POST"])
def submit_edit(doc_name):
    pending_edit_file = "{}/edit_{}.json".format(PENDING,doc_name)
    approved_file = "{}/{}.json".format(DATA_FOLDER,doc_name)

    if os.path.exists(approved_file):
        with open(approved_file, "r") as f:
            original_doc = json.load(f)

        updated_data = request.json
        #print(updated_data['resources'])
        #updated_data["status"] = "pending edit"
        #updated_data["original"] = original_doc  # Save original version inside edit file

        with open(pending_edit_file, "w+") as f:
            json.dump(updated_data, f, indent=4)

        return jsonify({"message": "Edited document submitted for review!"})
    else:
        print(approved_file,' not found')

    return jsonify({"error": "Original document not found"}), 404

#Review the edited document and either approve or reject it
@app.route("/review_edit/<doc_id>")
def review_edit(doc_id):
    original_file = doc_id.strip('edit_')
    approved_file = f"{DATA_FOLDER}/{original_file}"
    pending_edit_file = f"{PENDING}/{doc_id}" #doc_id is actually document name

    #print(approved_file)
    #print(pending_edit_file)

    if os.path.exists(approved_file) and os.path.exists(pending_edit_file):
        with open(approved_file, "r") as f:
            original_doc = json.load(f)

        with open(pending_edit_file, "r") as f:
            edited_doc = json.load(f)

        original_doc['name'] = original_file
        edited_doc['name'] = doc_id
        return render_template("review_edit_document.html", original=original_doc, edited=edited_doc)

    return "Document not found", 404


#Approve the editing of a pre-existing document
@app.route("/approve_edit/<doc_id>", methods=["POST"])
def approve_edit(doc_id):
    original_file = doc_id.strip('edit_')
    pending_edit_file = f"{PENDING}/{doc_id}"
    approved_file = f"{DATA_FOLDER}/{original_file}"

    if os.path.exists(pending_edit_file):
        with open(pending_edit_file, "r") as f:
            edited_doc = json.load(f)

        edited_doc["last_updated"] = str(datetime.utcnow().date())

        edited_doc['tags'] = edited_doc['tags'].split(',')
        #print(type(edited_doc["resources"]))

        with open(approved_file, "w+") as f:
            json.dump(edited_doc, f, indent=4)

        os.remove(pending_edit_file)  # Remove pending edit

        all_documents = load_documents()
        tokenized_docs = [preprocess_data(doc) for doc in all_documents]
        bm25 = BM25Okapi(tokenized_docs)

        return jsonify({"message": "Edited document approved and updated!"})

    return jsonify({"error": "Edited document not found"}), 404

#Reject the edits of a pre-existing document
@app.route("/reject_edit/<doc_id>", methods=["POST"])
def reject_edit(doc_id):
    pending_edit_file = f"{PENDING}/{doc_id}"

    if os.path.exists(pending_edit_file):
        os.remove(pending_edit_file)  # Delete rejected edits
        return jsonify({"message": "Edited document rejected!"})

    return jsonify({"error": "Edited document not found"}), 404


# Dummy dataset for demonstration
all_documents = load_documents()
print('Got All Documents')
tokenized_docs = [preprocess_data(doc) for doc in all_documents]
print('tokenization Done')
bm25 = BM25Okapi(tokenized_docs)
print('BM25 Index Computed')
pending_doc = 0

if __name__ == "__main__":
    app.run(debug=True)
