import pika
import time

# Conexão com RabbitMQ
conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = conn.channel()

# Declara fila genérica de promoções
channel.queue_declare(queue="promocoes")

print("[MS Marketing] Enviando promoções genéricas...")

try:
    while True:
        mensagem = "Promoção imperdível nos cruzeiros desta semana!"
        channel.basic_publish(exchange='', routing_key="promocoes", body=mensagem)
        print(f"[x] Promoção enviada: {mensagem}")
        time.sleep(5)
except KeyboardInterrupt:
    conn.close()
    print("[MS Marketing] Encerrado.")