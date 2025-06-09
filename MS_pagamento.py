import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import pika
import requests

app = Flask(__name__)

CORS(app)

# Armazena pagamentos pendentes aguardando callback
pendentes = {}

# --- Endpoint para solicitar pagamento ---
@app.route('/pagamento', methods=['POST'])
def solicitar_pagamento():
    dados = request.get_json()
    reserva_id = dados.get('reserva_id')
    valor = dados.get('valor')

    if not reserva_id or valor is None:
        return jsonify({'erro': 'Campos obrigatórios: reserva_id, valor'}), 400

    pendentes[reserva_id] = {
        'reserva_id': reserva_id,
        'valor': valor
    }

    link_pagamento = f"http://pagamento.fake/pagar?reserva_id={reserva_id}"
    return jsonify({'link': link_pagamento})

# --- Webhook simulado do sistema de pagamento externo ---
@app.route('/webhook', methods=['POST'])
def receber_webhook():
    notificacao = request.get_json()
    reserva_id = notificacao.get('reserva_id')
    status = notificacao.get('status')  # 'aprovado' ou 'recusado'

    if reserva_id not in pendentes:
        return jsonify({'erro': 'Reserva desconhecida'}), 404

    cliente_id = None
    try:
        r = requests.get(f"http://localhost:5000/reserva/{reserva_id}")
        if r.ok:
            cliente_id = r.json().get('cliente_id')
    except Exception:
        pass

    envelope = {
        'data': {
            'reserva_id': reserva_id,
            'status': status,
            'cliente_id': cliente_id
        }
    }
    routing_key = 'pagamento-aprovado' if status == 'aprovado' else 'pagamento-recusado'

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.exchange_declare(exchange='pagamento', exchange_type='direct')

        channel.basic_publish(
            exchange='pagamento',
            routing_key=routing_key,
            body=json.dumps(envelope)
        )

        print(f"[Webhook] Pagamento {status.upper()} para reserva {reserva_id}")
        pendentes.pop(reserva_id)
        connection.close()
        return jsonify({'mensagem': f'Pagamento {status} processado com sucesso'})
    except Exception as e:
        return jsonify({'erro': f'Erro ao publicar mensagem: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(port=5002)  # MS Pagamento na porta 5002
