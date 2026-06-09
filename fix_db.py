content = open('app.py', encoding='utf-8').read()

old = """def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn"""

new = """def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, timeout=30, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()"""

content = content.replace(
    'from flask import Flask, jsonify, redirect, render_template, request, session, url_for',
    'from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for'
)

result = content.replace(old, new)
open('app.py', 'w', encoding='utf-8').write(result)
print('OK - app.py modifie')