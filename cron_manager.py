#!/usr/bin/env python3
"""
Gerenciador de Cron Jobs
Lógica para criar, listar, alterar e excluir cron jobs
"""

import json
import os
import re
import subprocess
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class CronManager:
    def __init__(self, data_file='/data/cron.json'):
        self.data_file = data_file
        self.jobs = self._load_jobs()
        self._ensure_cron_running()
        self._sync_to_crontab()
    
    def _ensure_cron_running(self):
        """Garante que o crond está rodando"""
        try:
            subprocess.run(['crond'], check=False)
            logger.info("Crond iniciado")
        except Exception as e:
            logger.warning(f"Erro ao iniciar crond: {e}")
    
    def is_cron_running(self) -> bool:
        """Verifica se o crond está rodando"""
        try:
            result = subprocess.run(
                ['pgrep', 'crond'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _load_jobs(self) -> List[Dict]:
        """Carrega jobs do arquivo JSON"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar jobs: {e}")
                return []
        return []
    
    def _save_jobs(self):
        """Salva jobs no arquivo JSON"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w') as f:
                json.dump(self.jobs, f, indent=2)
            self._sync_to_crontab()
        except Exception as e:
            logger.error(f"Erro ao salvar jobs: {e}")
            raise
    
    def _validate_cron_schedule(self, schedule: str) -> bool:
        """Valida expressão cron"""
        # Padrão básico de expressão cron
        cron_pattern = r'^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])|\*/[0-9]+|[0-9]+-[0-9]+|[0-9]+(,[0-9]+)*)\s+' \
                       r'(\*|([0-9]|1[0-9]|2[0-3])|\*/[0-9]+|[0-9]+-[0-9]+|[0-9]+(,[0-9]+)*)\s+' \
                       r'(\*|([1-9]|1[0-9]|2[0-9]|3[0-1])|\*/[0-9]+|[0-9]+-[0-9]+|[0-9]+(,[0-9]+)*)\s+' \
                       r'(\*|([1-9]|1[0-2])|\*/[0-9]+|[0-9]+-[0-9]+|[0-9]+(,[0-9]+)*)\s+' \
                       r'(\*|[0-7]|\*/[0-9]+|[0-9]+-[0-9]+|[0-9]+(,[0-9]+)*)$'
        
        return bool(re.match(cron_pattern, schedule.strip()))
    
    def _sync_to_crontab(self):
        """Sincroniza jobs com o crontab"""
        try:
            crontab_content = ""
            for job in self.jobs:
                # Adiciona comentário com o ID e nome do job
                crontab_content += f"# ID: {job['id']} - {job['name']}\n"
                crontab_content += f"{job['schedule']} {job['command']}\n"
            
            # Escreve no crontab
            process = subprocess.Popen(
                ['crontab', '-'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(input=crontab_content.encode())
            
            if process.returncode != 0:
                logger.error(f"Erro ao atualizar crontab: {stderr.decode()}")
            else:
                logger.info("Crontab atualizado com sucesso")
                
        except Exception as e:
            logger.error(f"Erro ao sincronizar crontab: {e}")
            raise
    
    def list_jobs(self) -> List[Dict]:
        """Lista todos os jobs"""
        return self.jobs
    
    def get_job(self, job_id: int) -> Optional[Dict]:
        """Obtém um job específico"""
        for job in self.jobs:
            if job['id'] == job_id:
                return job
        return None
    
    def create_job(self, name: str, schedule: str, command: str) -> Dict:
        """Cria um novo job"""
        # Validações
        if not name or not name.strip():
            raise ValueError("Nome é obrigatório")
        
        if not self._validate_cron_schedule(schedule):
            raise ValueError("Expressão cron inválida")
        
        if not command or not command.strip():
            raise ValueError("Comando é obrigatório")
        
        # Gera ID
        new_id = max([job['id'] for job in self.jobs], default=0) + 1
        
        # Cria job
        job = {
            'id': new_id,
            'name': name.strip(),
            'schedule': schedule.strip(),
            'command': command.strip(),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.jobs.append(job)
        self._save_jobs()
        
        logger.info(f"Job criado: {job['name']} (ID: {job['id']})")
        return job
    
    def update_job(self, job_id: int, name: Optional[str] = None, 
                   schedule: Optional[str] = None, 
                   command: Optional[str] = None) -> Optional[Dict]:
        """Atualiza um job existente"""
        job = self.get_job(job_id)
        
        if not job:
            return None
        
        # Atualiza campos fornecidos
        if name is not None:
            if not name.strip():
                raise ValueError("Nome não pode ser vazio")
            job['name'] = name.strip()
        
        if schedule is not None:
            if not self._validate_cron_schedule(schedule):
                raise ValueError("Expressão cron inválida")
            job['schedule'] = schedule.strip()
        
        if command is not None:
            if not command.strip():
                raise ValueError("Comando não pode ser vazio")
            job['command'] = command.strip()
        
        job['updated_at'] = datetime.now().isoformat()
        self._save_jobs()
        
        logger.info(f"Job atualizado: {job['name']} (ID: {job['id']})")
        return job
    
    def delete_job(self, job_id: int) -> bool:
        """Exclui um job"""
        initial_count = len(self.jobs)
        self.jobs = [job for job in self.jobs if job['id'] != job_id]
        
        if len(self.jobs) < initial_count:
            self._save_jobs()
            logger.info(f"Job excluído: ID {job_id}")
            return True
        
        return False