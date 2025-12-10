import netifaces

def get_main_local_ip():
    gws = netifaces.gateways()
    default_iface = gws['default'].get(netifaces.AF_INET)
    
    if not default_iface:
        return None, None

    iface_name = default_iface[1]
    addrs = netifaces.ifaddresses(iface_name)
    inet = addrs.get(netifaces.AF_INET)

    if inet:
        if len(inet) > 0:
            ip_info = inet[0]
            ip_address = ip_info.get('addr')
            netmask = ip_info.get('netmask')
            return ip_address, netmask
    
    return None, None