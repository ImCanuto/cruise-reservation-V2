import json
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
import pika
import threading
import requests

app = Flask(__name__)
CORS(app)

# Armazenamento em memória
reservas = {}
interesses = set()

# Conexão principal para publicar
conn_pub = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel_pub = conn_pub.channel()

# Declara filas locais (publicação)
for q in ['reserva-criada', 'reserva-cancelada', 'pagamento-aprovado', 'pagamento-recusado', 'bilhete-gerado']:
    channel_pub.queue_declare(queue=q)

# --- Consumo de mensagens (pagamento/bilhete) ---
def start_consuming():
    conn_cons = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel_cons = conn_cons.channel()

    # Vincular filas à exchange
    channel_cons.exchange_declare(exchange='pagamento', exchange_type='direct')
    channel_cons.queue_declare(queue='pagamento-aprovado')
    channel_cons.queue_declare(queue='pagamento-recusado')
    channel_cons.queue_bind(exchange='pagamento', queue='pagamento-aprovado', routing_key='pagamento-aprovado')
    channel_cons.queue_bind(exchange='pagamento', queue='pagamento-recusado', routing_key='pagamento-recusado')

    for q in ['pagamento-aprovado', 'pagamento-recusado', 'bilhete-gerado']:
        channel_cons.queue_declare(queue=q)

    def on_message(ch, method, props, body):
        queue = method.routing_key
        if queue == 'bilhete-gerado':
            info = json.loads(body)
            print(f"[Reserva {info['reserva_id']}] Bilhete gerado: {info['bilhete_id']}")
        elif queue.startswith('pagamento-'):
            envelope = json.loads(body)
            print("===> pagamento-recusado recebido:", envelope)
            data = envelope['data']
            res_id = data['reserva_id']
            if queue == 'pagamento-aprovado':
                print(f"[Reserva {res_id}] Pagamento aprovado!")
            else:
                print(f"[Reserva {res_id}] Pagamento recusado e reserva cancelada.")
                if res_id in reservas:
                    dados = reservas.pop(res_id)
                    cancelamento = {
                        'reserva_id': res_id,
                        'itinerario_id': dados['itinerario_id'],
                        'cabines': dados['cabines']
                    }
                    channel_cons.basic_publish(exchange='', routing_key='reserva-cancelada', body=json.dumps(cancelamento))

    for q in ['pagamento-aprovado', 'pagamento-recusado', 'bilhete-gerado']:
        channel_cons.basic_consume(queue=q, on_message_callback=on_message, auto_ack=True)
    print("[Reserva] Iniciando consumo de eventos...")
    channel_cons.start_consuming()

threading.Thread(target=start_consuming, daemon=True).start()

# --- Endpoints REST ---

@app.route('/itinerarios', methods=['GET'])
def consultar_itinerarios():
    try:
        response = requests.get('http://localhost:5001/itinerarios', params=request.args)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'erro': 'Falha ao consultar itinerários', 'detalhes': str(e)}), 500

@app.route('/reserva', methods=['POST'])
def criar_reserva():
    dados = request.get_json()
    cliente_id = dados.get('cliente_id')
    it_id = dados.get('itinerario_id')
    pax = int(dados.get('passageiros', 1))
    cab = int(dados.get('cabines', 1))
    valor_total = float(dados.get('valor_total', 0))

    res_id = str(uuid.uuid4())
    reservas[res_id] = {
        'reserva_id': res_id,
        'cliente_id': cliente_id,
        'itinerario_id': it_id,
        'passageiros': pax,
        'cabines': cab
    }

    msg = {
        'reserva_id': res_id,
        'cliente_id': cliente_id,
        'itinerario_id': it_id,
        'passageiros': pax,
        'cabines': cab
    }
    channel_pub.basic_publish(exchange='', routing_key='reserva-criada', body=json.dumps(msg))

    try:
        pagamento_resp = requests.post('http://localhost:5002/pagamento', json={
            'reserva_id': res_id,
            'valor': valor_total
        })
        link = pagamento_resp.json().get('link')
    except Exception:
        link = f"http://pagamento.fake/pag?reserva_id={res_id}"

    return jsonify({'reserva_id': res_id, 'link_pagamento': link}), 201

@app.route('/reserva/<res_id>', methods=['GET'])
def consultar_reserva(res_id):
    if res_id in reservas:
        return jsonify(reservas[res_id])
    return jsonify({'erro': 'Reserva não encontrada'}), 404

@app.route('/reserva/<res_id>', methods=['DELETE'])
def cancelar_reserva(res_id):
    if res_id not in reservas:
        return jsonify({'erro': 'Reserva não encontrada'}), 404

    dados = reservas.pop(res_id)
    cancelamento = {
        'reserva_id': res_id,
        'itinerario_id': dados['itinerario_id'],
        'cabines': dados['cabines']
    }
    channel_pub.basic_publish(exchange='', routing_key='reserva-cancelada', body=json.dumps(cancelamento))
    return jsonify({'mensagem': 'Reserva cancelada com sucesso'})

@app.route('/reservas/<cliente_id>', methods=['GET'])
def listar_reservas_cliente(cliente_id):
    resultado = [r for r in reservas.values() if r.get('cliente_id') == cliente_id]
    return jsonify(resultado)

@app.route('/interesse/<cliente_id>', methods=['POST'])
def registrar_interesse(cliente_id):
    interesses.add(cliente_id)
    return jsonify({'mensagem': f'Cliente {cliente_id} registrado para promoções'})

@app.route('/interesse/<cliente_id>', methods=['DELETE'])
def cancelar_interesse(cliente_id):
    interesses.discard(cliente_id)
    return jsonify({'mensagem': f'Cliente {cliente_id} removido das promoções'})

if __name__ == '__main__':
    app.run(port=5000)  # MS Reserva na porta 5000
