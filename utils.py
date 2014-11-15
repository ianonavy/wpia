from flask import g, redirect, url_for
import simpleldap

import config


def ldap_fetch(uid=None, name=None, passwd=None):
    # try:
    result = None
    if name is not None and passwd is not None:
        # weird hack to auth with WPI CCC
        conn = simpleldap.Connection(
            config.LDAP_SERVER,
            port=config.LDAP_PORT,
            require_cert=False,
            dn=config.BIND_DN, password=config.LDAP_PASSWORD,
            encryption='ssl')
        res = conn.search('uid={0}'.format(name), base_dn=config.BASE_DN)
        dn = config.BIND_DN_FORMAT.format(res[0]['wpieduPersonUUID'][0])
        try:
            conn2 = simpleldap.Connection(
                config.LDAP_SERVER,
                port=config.LDAP_PORT,
                require_cert=False,
                dn=dn, password=passwd,
                encryption='ssl')
            result = conn.search('uid={0}'.format(name), base_dn=config.BASE_DN)
        except:
            return None
    else:
        conn = simpleldap.Connection(config.LDAP_SERVER)
        result = conn.search(
            'uidNumber={0}'.format(uid),
            base_dn=config.BASE_DN)

    if result:
        return {
            'name': result[0]['gecos'][0].split(' ')[0],
            'uid': result[0]['uid'][0],
            'id': unicode(result[0]['uidNumber'][0]),
            'gid': int(result[0]['gidNumber'][0]),
            'mail': result[0]['mail'][0]
        }
    else:
        return None
