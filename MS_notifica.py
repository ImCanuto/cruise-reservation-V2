from flask import Flask, Response, request
from flask_cors import CORS
import pika, json, threading, queue

app = Flask(__name__)
CORS(app)

clientes = {}  # cliente_id -> Queue
clientes_inscritos = set()

@app.route('/eventos/<cliente_id>')
def sse(cliente_id):
    # Qualquer cliente pode receber eventos
    def stream():
        q = queue.Queue()
        clientes[cliente_id] = q
        try:
            while True:
                evento = q.get()
                yield f"data: {json.dumps(evento)}\n\n"
        except GeneratorExit:
            if cliente_id in clientes:
                clientes.pop(cliente_id)

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
                
    # Eventos específicos: para o cliente-alvo
    elif cliente_id:
        if cliente_id in clientes:
            clientes[cliente_id].put(evento)

def consumidor_background():
    conexao = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    canal = conexao.channel()

    # Filas para todos os tipos de eventos
    filas = ['promocoes', 'pagamento-aprovado', 'pagamento-recusado', 'bilhete-gerado']
    
    for fila in filas:
        canal.queue_declare(queue=fila)

        def callback(ch, method, properties, body):
            tipo_evento = method.routing_key
            try:
                data = json.loads(body)
            except:
                data = {'mensagem': body.decode()}

            # Processar diferentes tipos de eventos
            if tipo_evento == 'promocoes':
                evento = {
                    'tipo': 'promocao',
                    'mensagem': data.get('mensagem', 'Nova promoção disponível!')
                }
                
            elif tipo_evento in ('pagamento-aprovado', 'pagamento-recusado'):
                # Para eventos de pagamento, extrair dados do envelope
                payload = data.get('data', {})
                evento = {
                    'tipo': 'pagamento',
                    'reserva_id': payload.get('reserva_id', ''),
                    'cliente_id': payload.get('cliente_id', ''),
                    'status': 'aprovado' if tipo_evento == 'pagamento-aprovado' else 'recusado'
                }
                
            elif tipo_evento == 'bilhete-gerado':
                # Evento de bilhete gerado
                evento = {
                    'tipo': 'bilhete',
                    'reserva_id': data.get('reserva_id', ''),
                    'bilhete_id': data.get('bilhete_id', ''),
                    'destino': data.get('destino', ''),
                    'cliente_id': data.get('cliente_id', '')
                }
                
            else:
                # Outros eventos
                evento = {
                    'tipo': tipo_evento.replace('-', '_'),
                    'dados': data
                }
            
            print(f"[Notificações] Evento processado: {evento}")
            distribuir_evento(evento)

        canal.basic_consume(queue=fila, on_message_callback=callback, auto_ack=True)

    print("[Notificações] Aguardando eventos...")
    canal.start_consuming()

threading.Thread(target=consumidor_background, daemon=True).start()

if __name__ == '__main__':
    app.run(port=5003)