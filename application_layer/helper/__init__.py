import requests
import ipaddress

# Fetch the IP ranges from Atlassian
def get_atlassian_ip_ranges():

    url = "https://ip-ranges.atlassian.com/"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        ip_ranges = data.get("items", [])
    else:
        raise Exception("Failed to fetch IP ranges from Atlassian.")
    
    networks = []
    for item in ip_ranges:
        network = item.get("cidr")
        if network:
            networks.append(ipaddress.ip_network(network))
    return networks

def get_ip_ranges(ip_ranges):
    networks = []
    for item in ip_ranges:
        network = item.get("cidr")
        if network:
            networks.append(ipaddress.ip_network(network))
    return networks





# Check if an IP is in the Atlassian IP range
def is_ip_in_authorized_ranges(ip, ip_ranges):
    ip_addr = ipaddress.ip_address(ip)
    for network in ip_ranges:
        if ip_addr in network:
            return True
    return False
