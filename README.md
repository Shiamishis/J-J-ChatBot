1. Create Data Folder and add all documentation + excel files
2. Run all scripts from root
3. run all scripts within the scripts folder (for the metadata one should run as  python .\build_metadata.py --db 'local.db')
4. run main as: uvicorn src.Server.main:app --reload




Frontend:
1. Post everything online using Azure and running it on the cloud (to do that you first create an app in Azure and then you push the entire codebas including data to the cloud and run it using  az webapp up --name chatbotjnj --resource-group chatbotjnj_rg_final , where --name is the name of the app)
2. Create power automate workflow that takes the cloud link and then with an Http block it gets the request and parses it to power app
3. in power app create the interface of the response
4. in power bi drag the power app you just created (weird bug: have to initiate different plot and populate it before using a power app, else it does not recognize it)
