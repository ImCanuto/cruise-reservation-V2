import json
import threading
from flask import Flask, request, jsonify
import pika

app = Flask(__name__)

# Carrega os itinerários do arquivo JSON e adiciona o campo de disponibilidade
with open('data/itinerarios.json') as f:
    raw_itinerarios = json.load(f)

itinerarios = {}
for it in raw_itinerarios:
    it['cabines_disponiveis'] = 10  # valor fixo inicial
    itinerarios[it['id']] = it

# --- API REST ---
@app.route('/itinerarios', methods=['GET'])
def get_itinerarios():
    destino = request.args.get('destino')
    data = request.args.get('data_partida')
    porto = request.args.get('porto_embarque')

    resultado = []
    for it in itinerarios.values():
        if destino and destino.lower() not in it['destino'].lower():
            continue
        if data and data != it['data_partida']:
            continue
        if porto and porto.lower() not in it['porto_embarque'].lower():
            continue
        resultado.append(it)

    return jsonify(resultado)

# --- RabbitMQ Consumer ---
def callback(ch, method, props, body):
    msg = json.loads(body)
    itin_id = msg.get('itinerario_id')
    qtd = int(msg.get('cabines', 1))  # default: 1 cabine se não informado

    if itin_id not in itinerarios:
        print(f"[!] Itinerário '{itin_id}' não encontrado.")
        return

    if method.routing_key == 'reserva-criada':
        itinerarios[itin_id]['cabines_disponiveis'] -= qtd
        print(f"[-] Reserva criada: -{qtd} cabines em {itin_id}")
    elif method.routing_key == 'reserva-cancelada':
        itinerarios[itin_id]['cabines_disponiveis'] += qtd
        print(f"[+] Reserva cancelada: +{qtd} cabines em {itin_id}")

    # Limita disponibilidade ao máximo de 10
    itinerarios[itin_id]['cabines_disponiveis'] = min(itinerarios[itin_id]['cabines_disponiveis'], 10)


def consume_rabbitmq():
    conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    ch = conn.channel()
    ch.queue_declare(queue='reserva-criada')
    ch.queue_declare(queue='reserva-cancelada')

    ch.basic_consume(queue='reserva-criada', on_message_callback=callback, auto_ack=True)
    ch.basic_consume(queue='reserva-cancelada', on_message_callback=callback, auto_ack=True)

    print("[MS Itinerários] Aguardando mensagens de reserva...")
    ch.start_consuming()

if __name__ == '__main__':
    threading.Thread(target=consume_rabbitmq, daemon=True).start()
    app.run(port=5001)
