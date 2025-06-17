import socket
from dnslib import DNSRecord
import time


def test_dns():
    print("Подготавливаем DNS запрос...")
    query = DNSRecord.question("google.com")
    query_data = query.pack()

    print("Отправляем запрос к 127.0.0.1:8053...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)

    try:
        sock.sendto(query_data, ('127.0.0.1', 8053))
        print("Ожидаем ответ...")
        start_time = time.time()
        response = sock.recv(2048)
        elapsed = time.time() - start_time

        print(f"Ответ получен за {elapsed:.2f} сек:")
        print(DNSRecord.parse(response))

    except socket.timeout:
        print("Таймаут: сервер не ответил за 3 секунды")
    except Exception as e:
        print(f"Ошибка: {str(e)}")
    finally:
        sock.close()


if __name__ == "__main__":
    test_dns()