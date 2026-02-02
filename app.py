#!/usr/bin/env python3
"""
Cron Manager API
API REST para gerenciar cron jobs em container
"""

from flask import Flask, redirect, url_for
from flask_restx import Api, Resource, fields, reqparse
from cron_manager import CronManager
import logging
import os

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
api = Api(
    app,
    version='1.0',
    title='Cron Manager API',
    description='API REST para gerenciar cron jobs em container Docker com timezone de Brasília (UTC-3)'
)

cron_manager = CronManager()

# Modelos para documentação
dados_cron_model = api.model('DadosCron', {
    'periodicidade': fields.Integer(required=True, description='Periodicidade: 1=diário, 2=semanal, 3=mensal', example=1),
    'dias': fields.List(fields.Integer, description='Dias para execução (1-28)', example=[1, 15]),
    'horario': fields.String(required=True, description='Horário inicial (HH:MM)', example='09:00'),
    'recorrencia': fields.String(required=True, description='Recorrência (ex: 1min, 15min, 1h, 2h)', example='1h')
})

agendamento_model = api.model('Agendamento', {
    'idAgendamento': fields.Integer(description='ID único do agendamento', example=1),
    'nomeAgendamento': fields.String(required=True, description='Nome do agendamento', example='Backup diário'),
    'urlAgendamento': fields.String(required=True, description='URL para chamada HTTP', example='https://api.exemplo.com/backup'),
    'payloadAgendamento': fields.String(description='JSON payload para POST (opcional)', example='{"tipo": "backup", "data": "2026-02-02"}'),
    'dadosCron': fields.Nested(dados_cron_model, required=True, description='Configurações de agendamento'),
    'schedule': fields.String(description='Expressão cron gerada automaticamente', example='0 9 * * *'),
    'command': fields.String(description='Comando gerado automaticamente'),
    'slug': fields.String(description='Slug da URL para nome do log'),
    'created_at': fields.DateTime(description='Data de criação'),
    'updated_at': fields.DateTime(description='Data da última atualização')
})

agendamento_input = api.model('AgendamentoInput', {
    'nomeAgendamento': fields.String(required=True, description='Nome do agendamento', example='Backup diário'),
    'urlAgendamento': fields.String(required=True, description='URL para chamada HTTP', example='https://api.exemplo.com/backup'),
    'payloadAgendamento': fields.String(description='JSON payload para POST (opcional)', example='{"tipo": "backup", "data": "2026-02-02"}'),
    'dadosCron': fields.Nested(dados_cron_model, required=True, description='Configurações de agendamento')
})

agendamento_update = api.model('AgendamentoUpdate', {
    'nomeAgendamento': fields.String(description='Nome do agendamento', example='Backup diário atualizado'),
    'urlAgendamento': fields.String(description='URL para chamada HTTP', example='https://api.exemplo.com/backup-v2'),
    'payloadAgendamento': fields.String(description='JSON payload para POST (opcional)', example='{"tipo": "backup", "versao": "2.0"}'),
    'dadosCron': fields.Nested(dados_cron_model, description='Configurações de agendamento')
})

response_model = api.model('Response', {
    'success': fields.Boolean(description='Status da operação'),
    'message': fields.String(description='Mensagem de retorno'),
    'error': fields.String(description='Mensagem de erro')
})

health_model = api.model('Health', {
    'status': fields.String(description='Status do serviço', example='healthy'),
    'service': fields.String(description='Nome do serviço', example='cron-manager'),
    'cron_running': fields.Boolean(description='Status do daemon cron')
})

@api.route('/health')
class Health(Resource):
    @api.doc('health_check')
    @api.marshal_with(health_model)
    def get(self):
        """Health check endpoint"""
        return {
            'status': 'healthy',
            'service': 'cron-manager',
            'cron_running': cron_manager.is_cron_running()
        }

@app.route('/swagger/')
def swagger_ui():
    """Redirect para a documentação Swagger"""
    return redirect(url_for('doc'))

@api.route('/api/cron')
class CronJobList(Resource):
    @api.doc('list_agendamentos')
    @api.marshal_list_with(agendamento_model)
    def get(self):
        """Lista todos os agendamentos"""
        try:
            jobs = cron_manager.list_jobs()
            return jobs
        except Exception as e:
            logger.error(f"Erro ao listar agendamentos: {e}")
            api.abort(500, f"Erro interno: {str(e)}")
    
    @api.doc('create_agendamento')
    @api.expect(agendamento_input)
    @api.marshal_with(agendamento_model, code=201)
    def post(self):
        """Cria um novo agendamento"""
        try:
            data = api.payload
            
            # Criar agendamento
            job = cron_manager.create_job(
                nome_agendamento=data['nomeAgendamento'],
                url_agendamento=data['urlAgendamento'],
                dados_cron=data['dadosCron'],
                payload_agendamento=data.get('payloadAgendamento')
            )
            
            return job, 201
            
        except ValueError as e:
            api.abort(400, str(e))
        except Exception as e:
            logger.error(f"Erro ao criar agendamento: {e}")
            api.abort(500, f"Erro interno: {str(e)}")

@api.route('/api/cron/<int:job_id>')
class CronJob(Resource):
    @api.doc('get_agendamento')
    @api.marshal_with(agendamento_model)
    def get(self, job_id):
        """Obtém um agendamento específico"""
        try:
            job = cron_manager.get_job(job_id)
            if job:
                return job
            else:
                api.abort(404, 'Agendamento não encontrado')
        except Exception as e:
            logger.error(f"Erro ao obter agendamento: {e}")
            api.abort(500, f"Erro interno: {str(e)}")
    
    @api.doc('update_agendamento')
    @api.expect(agendamento_update)
    @api.marshal_with(agendamento_model)
    def put(self, job_id):
        """Atualiza um agendamento existente"""
        try:
            data = api.payload
            
            job = cron_manager.update_job(
                job_id=job_id,
                nome_agendamento=data.get('nomeAgendamento'),
                url_agendamento=data.get('urlAgendamento'),
                dados_cron=data.get('dadosCron'),
                payload_agendamento=data.get('payloadAgendamento')
            )
            
            if job:
                return job
            else:
                api.abort(404, 'Agendamento não encontrado')
                
        except ValueError as e:
            api.abort(400, str(e))
        except Exception as e:
            logger.error(f"Erro ao atualizar agendamento: {e}")
            api.abort(500, f"Erro interno: {str(e)}")
    
    @api.doc('delete_agendamento')
    @api.marshal_with(response_model)
    def delete(self, job_id):
        """Exclui um agendamento"""
        try:
            if cron_manager.delete_job(job_id):
                return {
                    'success': True,
                    'message': 'Agendamento excluído com sucesso'
                }
            else:
                api.abort(404, 'Agendamento não encontrado')
        except Exception as e:
            logger.error(f"Erro ao excluir agendamento: {e}")
            api.abort(500, f"Erro interno: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'cron-manager',
        'cron_running': cron_manager.is_cron_running()
    }), 200

@app.route('/api/cron', methods=['GET'])
def list_crons():
    """Lista todos os cron jobs"""
    try:
        jobs = cron_manager.list_jobs()
        return jsonify({
            'success': True,
            'count': len(jobs),
            'jobs': jobs
        }), 200
    except Exception as e:
        logger.error(f"Erro ao listar cron jobs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cron/<int:job_id>', methods=['GET'])
def get_cron(job_id):
    """Obtém um cron job específico"""
    try:
        job = cron_manager.get_job(job_id)
        if job:
            return jsonify({
                'success': True,
                'job': job
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Job não encontrado'
            }), 404
    except Exception as e:
        logger.error(f"Erro ao obter cron job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cron', methods=['POST'])
def create_cron():
    """Cria um novo cron job"""
    try:
        data = request.get_json()
        
        # Validação básica
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não fornecidos'
            }), 400
        
        required_fields = ['name', 'schedule', 'command']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório ausente: {field}'
                }), 400
        
        # Criar job
        job = cron_manager.create_job(
            name=data['name'],
            schedule=data['schedule'],
            command=data['command']
        )
        
        return jsonify({
            'success': True,
            'message': 'Cron job criado com sucesso',
            'job': job
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Erro ao criar cron job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cron/<int:job_id>', methods=['PUT'])
def update_cron(job_id):
    """Atualiza um cron job existente"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não fornecidos'
            }), 400
        
        job = cron_manager.update_job(
            job_id=job_id,
            name=data.get('name'),
            schedule=data.get('schedule'),
            command=data.get('command')
        )
        
        if job:
            return jsonify({
                'success': True,
                'message': 'Cron job atualizado com sucesso',
                'job': job
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Job não encontrado'
            }), 404
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Erro ao atualizar cron job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cron/<int:job_id>', methods=['DELETE'])
def delete_cron(job_id):
    """Exclui um cron job"""
    try:
        if cron_manager.delete_job(job_id):
            return jsonify({
                'success': True,
                'message': 'Cron job excluído com sucesso'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Job não encontrado'
            }), 404
    except Exception as e:
        logger.error(f"Erro ao excluir cron job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint não encontrado'
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'success': False,
        'error': 'Erro interno do servidor'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)