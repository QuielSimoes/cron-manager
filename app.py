#!/usr/bin/env python3
"""
Cron Manager API
API REST para gerenciar cron jobs em container
"""

from flask import Flask, request, jsonify
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
cron_manager = CronManager()

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