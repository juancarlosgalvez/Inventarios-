import hashlib
from db import cursor


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def db_authenticate(username, password):
    cur = cursor()
    cur.execute('SELECT id, password_hash, display_name, role FROM users WHERE username=%s', (username,))
    row = cur.fetchone()
    if not row:
        return False, 'Usuario no encontrado'
    uid, ph, dname, role = row
    if sha256(password) == ph:
        return True, {'id': uid, 'username': username, 'display_name': dname, 'role': role}
    return False, 'Contraseña incorrecta'


# Optional LDAP auth (configure LDAP_ENABLED in UI or config file)
from ldap3 import Server, Connection, ALL
LDAP_ENABLED = False
LDAP_CONFIG = {
    'server': 'ldap://ldap.example.com',
    'user_dn_template': 'CN={username},OU=Users,DC=example,DC=com'
}


def ldap_authenticate(username, password):
    if not LDAP_ENABLED:
        return False, 'LDAP disabled'
    try:
        s = Server(LDAP_CONFIG['server'], get_info=ALL)
        dn = LDAP_CONFIG['user_dn_template'].format(username=username)
        c = Connection(s, user=dn, password=password, auto_bind=True) # Attempt to bind
        return True, {'username': username} # 
    except Exception as e:
        return False, str(e)