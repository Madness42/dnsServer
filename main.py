import socket
import time
from dnslib import DNSRecord, RCODE, RR

TRUST_SERVER = "77.88.8.1"


class Cache:
    def __init__(self):
        self.cache = dict()

    def save_cache(self, path):
        with open(path, "w", encoding="utf-8") as f:
            for (rtype, rname), (records, ttl) in self.cache.items():
                if time.time() < ttl:
                    for record in records:
                        f.write(f"{rtype};{str(rname)};{ttl};{record.toZone()}\n")

    def load_cache(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(";")
                    if len(parts) != 4:
                        continue
                    rtype = int(parts[0])
                    rname = parts[1]
                    ttl = float(parts[2])
                    zone_str = parts[3]
                    if time.time() < ttl:
                        rr = RR.fromZone(zone_str)[0]
                        key = (rtype, rr.rname)
                        if key not in self.cache:
                            self.cache[key] = ([], ttl)
                        self.cache[key][0].append(rr)
        except FileNotFoundError:
            pass

    def update_cache(self, key, records, ttl):
        self.cache[key] = (records, time.time() + ttl)

    def get_cache(self, key):
        entry = self.cache.get(key)
        if not entry:
            return None
        records, ttl = entry
        if time.time() > ttl:
            del self.cache[key]
            return None
        return records


class DNS:
    def __init__(self):
        self.cache = Cache()
        self.cache.load_cache("cache.txt")

    def process(self, query_data):
        try:
            query = DNSRecord.parse(query_data)
            query_key = (query.q.qtype, query.q.qname)

            rdata = self.cache.get_cache(query_key)
            if rdata:
                response = DNSRecord(header=query.header)
                response.add_question(query.q)
                response.rr.extend(rdata)
                print(f"Найдено в кэше:\n{response}\n")
                return response.pack()

            response_data = query.send(TRUST_SERVER, 53, timeout=5)
            response = DNSRecord.parse(response_data)

            if response.header.rcode == RCODE.NOERROR:
                for section in (response.rr, response.auth, response.ar):
                    for rr in section:
                        key = (rr.rtype, rr.rname)
                        self.cache.update_cache(key, [rr], rr.ttl)
            self.cache.save_cache("cache.txt")
            return response.pack()

        except Exception as e:
            print(f"Ошибка при обработке запроса: {e}")
            return None


LOCALHOST = "localhost"
DEFAULT_PORT = 8053


def main():
    print(f"DNS сервер запущен на {LOCALHOST}:{DEFAULT_PORT}")
    print("Ожидание запросов... (Ctrl+C для остановки)")
    dns_server = DNS()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LOCALHOST, DEFAULT_PORT))

    try:
        while True:
            query, addr = sock.recvfrom(2048)
            rdata = dns_server.process(query)
            if rdata:
                sock.sendto(rdata, addr)
    except KeyboardInterrupt:
        dns_server.cache.save_cache("cache.txt")
        sock.close()


if __name__ == "__main__":
    main()
