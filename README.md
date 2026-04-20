1. Create Data Folder and add all documentation + excel files
2. Run all scripts from root
3. run all scripts within the scripts folder (for the metadata one should run as  python .\build_metadata.py --db 'local.db')
4. run main as: uvicorn src.Server.main:app --reload
