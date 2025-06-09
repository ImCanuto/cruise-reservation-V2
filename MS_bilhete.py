import pika
import json
import uuid

# Mapeia destinos
with open('data/itinerarios.json') as f:
    itinerarios = json.load(f)

# Conecta ao RabbitMQ
conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
ch = conn.channel()

# Declara exchange e fila
ch.exchange_declare(exchange='pagamento', exchange_type='direct')
queue_name = ch.queue_declare(queue='', exclusive=True).method.queue
ch.queue_bind(exchange='pagamento', queue=queue_name, routing_key='pagamento-aprovado')

print("[MS Bilhete] Aguardando pagamentos aprovados...")

def callback(ch_, method, props, body):
    env = json.loads(body)
    data = env['data']

    res_id = data['reserva_id']
    itin_id = data.get('itinerario_id')
    cliente_id = data.get('cliente_id')
    destino = next((it['destino'] for it in itinerarios if it['id'] == itin_id), 'Desconhecido')

    bil_id = str(uuid.uuid4())
    payload = {
        'reserva_id': res_id,
        'bilhete_id': bil_id,
        'destino': destino,
        'cliente_id': cliente_id
    }

    ch.basic_publish(exchange='', routing_key='bilhete-gerado', body=json.dumps(payload))
    print(f"[x] Bilhete gerado para {res_id}: {bil_id} ({destino})")

ch.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
ch.start_consuming()
