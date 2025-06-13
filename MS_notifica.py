from flask import Flask, Response, request
from flask_cors import CORS
import pika, json, threading, queue

app = Flask(__name__)
CORS(app)

clientes = {}  # cliente_id -> Queue
clientes_inscritos = set()

@app.route('/eventos/<cliente_id>')
def sse(cliente_id):
    # Removida a verificação de inscrição - qualquer cliente pode receber eventos
    def stream():
        q = queue.Queue()
        clientes[cliente_id] = q
        try:
            while True:
                evento = q.get()
                yield f"data: {json.dumps(evento)}\n\n"
        except GeneratorExit:
            clientes.pop(cliente_id, None)

    return Response(stream(), mimetype='text/event-stream')

@app.route('/interesse/<cliente_id>', methods=['POST'])
def registrar_interesse(cliente_id):
    clientes_inscritos.add(cliente_id)
    return {"status": "registrado"}, 200

@app.route('/interesse/<cliente_id>', methods=['DELETE'])
def cancelar_interesse(cliente_id):
    clientes_inscritos.discard(cliente_id)
    if cliente_id in clientes:
        clientes.pop(cliente_id, None)
    return {"status": "cancelado"}, 200

def distribuir_evento(evento):
    tipo = evento.get('tipo')
    cliente_id = evento.get('cliente_id')
    
    # Promoções: apenas para clientes inscritos
    if tipo == 'promocao':
        for cid in clientes_inscritos:
            if cid in clientes:
                clientes[cid].put(evento)
                
    # Eventos específicos: para o cliente-alvo (sem necessidade de inscrição)
    elif cliente_id and cliente_id in clientes:
        clientes[cliente_id].put(evento)

def consumidor_background():
    conexao = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    canal = conexao.channel()

    # Adicionado 'pagamento-recusado' para receber todos os status de pagamento
    filas = ['promocoes', 'pagamento-aprovado', 'pagamento-recusado', 'bilhete-gerado']
    
    for fila in filas:
        canal.queue_declare(queue=fila)

        def callback(ch, method, properties, body):
            tipo_evento = method.routing_key
            try:
                data = json.loads(body)
            except:
                data = {'mensagem': body.decode()}

            # Normaliza tipos de eventos
            if tipo_evento == 'promocoes':
                tipo_normalizado = 'promocao'
            elif tipo_evento.startswith('pagamento-'):
                tipo_normalizado = 'pagamento'
                # Adiciona status específico para pagamentos
                data['status'] = 'aprovado' if tipo_evento == 'pagamento-aprovado' else 'recusado'
            else:
                tipo_normalizado = tipo_evento.replace('-', '')

            # Para eventos de pagamento, extrai dados do envelope
            if tipo_normalizado == 'pagamento':
                payload = {
                    'tipo': tipo_normalizado,
                    'reserva_id': data['data']['reserva_id'],
                    'cliente_id': data['data']['cliente_id'],
                    'status': data['status']
                }
            else:
                payload = {'tipo': tipo_normalizado, **data}
                
            print(f"[Notificações] Evento '{tipo_evento}' processado")
            distribuir_evento(payload)

        canal.basic_consume(queue=fila, on_message_callback=callback, auto_ack=True)

    print("[Notificações] Aguardando eventos...")
    canal.start_consuming()

threading.Thread(target=consumidor_background, daemon=True).start()

if __name__ == '__main__':
    app.run(port=5003)