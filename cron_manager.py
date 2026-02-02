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
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class CronManager:
    def __init__(self, data_file='/data/cron.json'):
        self.data_file = data_file
        self.jobs = self._load_jobs()
        self._ensure_cron_running()
        self._sync_to_crontab()
    
    def _generate_url_slug(self, url: str) -> str:
        """Gera slug da URL para nome do arquivo de log"""
        # Remove protocolo e converte para minúsculo
        clean_url = re.sub(r'^https?://', '', url.lower())
        # Remove caracteres especiais e substitui por -
        slug = re.sub(r'[^a-z0-9]+', '-', clean_url)
        # Remove - do início e fim
        slug = slug.strip('-')
        return slug
    
    def _build_cron_expression(self, dados_cron: Dict) -> str:
        """Monta expressão cron baseada nos parâmetros"""
        periodicidade = dados_cron.get('periodicidade')
        dias = dados_cron.get('dias', [])
        horario = dados_cron.get('horario', '00:00')
        recorrencia = dados_cron.get('recorrencia', '1h')
        
        # Parse do horário
        try:
            hora, minuto = map(int, horario.split(':'))
        except:
            hora, minuto = 0, 0
        
        # Parse da recorrência
        recorrencia_num = 1
        recorrencia_unit = 'h'
        if recorrencia:
            match = re.match(r'(\d+)(min|h)', recorrencia)
            if match:
                recorrencia_num = int(match.group(1))
                recorrencia_unit = match.group(2)
        
        # Monta expressão baseada na periodicidade
        if periodicidade == 1:  # Diário
            if recorrencia_unit == 'min':
                return f'*/{recorrencia_num} {hora}-23 * * *'
            else:  # horas
                if recorrencia_num == 1:
                    return f'{minuto} {hora}-23 * * *'
                else:
                    # Gera lista de horas com recorrência
                    horas_list = []
                    for h in range(hora, 24, recorrencia_num):
                        horas_list.append(str(h))
                    horas_str = ','.join(horas_list)
                    return f'{minuto} {horas_str} * * *'
        
        elif periodicidade == 2:  # Semanal
            dias_semana = ','.join([str(d % 7) for d in dias if 1 <= d <= 7])
            if not dias_semana:
                dias_semana = '0'  # Domingo por padrão
            
            if recorrencia_unit == 'min':
                return f'*/{recorrencia_num} {hora}-23 * * {dias_semana}'
            else:
                if recorrencia_num == 1:
                    return f'{minuto} {hora}-23 * * {dias_semana}'
                else:
                    # Gera lista de horas com recorrência
                    horas_list = []
                    for h in range(hora, 24, recorrencia_num):
                        horas_list.append(str(h))
                    horas_str = ','.join(horas_list)
                    return f'{minuto} {horas_str} * * {dias_semana}'
        
        elif periodicidade == 3:  # Mensal
            dias_mes = ','.join([str(d) for d in dias if 1 <= d <= 28])
            if not dias_mes:
                dias_mes = '1'  # Dia 1 por padrão
            
            if recorrencia_unit == 'min':
                return f'*/{recorrencia_num} {hora}-23 {dias_mes} * *'
            else:
                if recorrencia_num == 1:
                    return f'{minuto} {hora}-23 {dias_mes} * *'
                else:
                    # Para recorrência em horas no mensal, usa apenas o horário inicial
                    horas_list = []
                    for h in range(hora, 24, recorrencia_num):
                        horas_list.append(str(h))
                    horas_str = ','.join(horas_list)
                    return f'{minuto} {horas_str} {dias_mes} * *'
        
        # Fallback para execução diária às 00:00
        return f'{minuto} {hora} * * *'
    
    def _build_curl_command(self, url: str, payload: str = None, slug: str = '') -> str:
        """Monta comando curl para execução"""
        log_file = f'/var/log/cron/{slug}.txt'
        
        if payload:
            # POST com payload JSON
            curl_cmd = f"curl -k -s -X POST '{url}' -H 'Content-Type: application/json' -d '{payload}'"
        else:
            # GET simples
            curl_cmd = f"curl -k -s '{url}'"
        
        # Adiciona redirecionamento para log com timestamp
        full_cmd = f'echo "[$(date)] Executando chamada para {url}" >> {log_file} && {curl_cmd} >> {log_file} 2>&1 && echo "[$(date)] Chamada concluída" >> {log_file}'
        
        return full_cmd
    
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
                job_id = job.get('idAgendamento', job.get('id'))
                job_name = job.get('nomeAgendamento', job.get('name'))
                crontab_content += f"# ID: {job_id} - {job_name}\n"
                # Adiciona redirecionamento para logs de erro
                crontab_content += f"{job['schedule']} {job['command']} 2>&1\n"
            
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
                # Reinicia o cron para garantir que as mudanças sejam aplicadas
                subprocess.run(['pkill', '-HUP', 'crond'], check=False)
                
        except Exception as e:
            logger.error(f"Erro ao sincronizar crontab: {e}")
            raise
    
    def list_jobs(self) -> List[Dict]:
        """Lista todos os jobs"""
        return self.jobs
    
    def get_job(self, job_id: int) -> Optional[Dict]:
        """Obtém um agendamento específico"""
        for job in self.jobs:
            if job.get('idAgendamento', job.get('id')) == job_id:
                return job
        return None
    
    def create_job(self, nome_agendamento: str, url_agendamento: str, 
                   dados_cron: Dict, payload_agendamento: str = None) -> Dict:
        """Cria um novo agendamento"""
        # Validações
        if not nome_agendamento or not nome_agendamento.strip():
            raise ValueError("Nome do agendamento é obrigatório")
        
        if not url_agendamento or not url_agendamento.strip():
            raise ValueError("URL do agendamento é obrigatória")
        
        if not dados_cron:
            raise ValueError("Dados do cron são obrigatórios")
        
        # Gera próximo ID
        next_id = max([job.get('idAgendamento', job.get('id', 0)) for job in self.jobs], default=0) + 1
        
        # Gera slug para log
        slug = self._generate_url_slug(url_agendamento)
        
        # Monta expressão cron
        schedule = self._build_cron_expression(dados_cron)
        
        # Monta comando curl
        command = self._build_curl_command(url_agendamento, payload_agendamento, slug)
        
        # Valida expressão cron
        if not self._validate_cron_schedule(schedule):
            raise ValueError(f"Expressão cron inválida: {schedule}")
        
        # Cria novo job
        new_job = {
            'idAgendamento': next_id,
            'nomeAgendamento': nome_agendamento.strip(),
            'urlAgendamento': url_agendamento.strip(),
            'payloadAgendamento': payload_agendamento,
            'dadosCron': dados_cron,
            'schedule': schedule,  # Gerado automaticamente
            'command': command,    # Gerado automaticamente
            'slug': slug,         # Para referência
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.jobs.append(new_job)
        self._save_jobs()
        
        logger.info(f"Agendamento criado: {nome_agendamento} (ID: {next_id})")
        return new_job
    
    def update_job(self, job_id: int, nome_agendamento: str = None, 
                   url_agendamento: str = None, dados_cron: Dict = None,
                   payload_agendamento: str = None) -> Optional[Dict]:
        """Atualiza um agendamento existente"""
        job = self.get_job(job_id)
        if not job:
            return None
        
        # Atualiza campos se fornecidos
        if nome_agendamento is not None:
            if not nome_agendamento.strip():
                raise ValueError("Nome do agendamento não pode ser vazio")
            job['nomeAgendamento'] = nome_agendamento.strip()
        
        if url_agendamento is not None:
            if not url_agendamento.strip():
                raise ValueError("URL do agendamento não pode ser vazia")
            job['urlAgendamento'] = url_agendamento.strip()
            job['slug'] = self._generate_url_slug(url_agendamento)
        
        if payload_agendamento is not None:
            job['payloadAgendamento'] = payload_agendamento
        
        if dados_cron is not None:
            job['dadosCron'] = dados_cron
        
        # Regenera schedule e command se necessário
        if dados_cron is not None or url_agendamento is not None or payload_agendamento is not None:
            job['schedule'] = self._build_cron_expression(job['dadosCron'])
            job['command'] = self._build_curl_command(
                job['urlAgendamento'], 
                job.get('payloadAgendamento'), 
                job['slug']
            )
            
            # Valida nova expressão cron
            if not self._validate_cron_schedule(job['schedule']):
                raise ValueError(f"Expressão cron inválida: {job['schedule']}")
        
        job['updated_at'] = datetime.now().isoformat()
        
        self._save_jobs()
        logger.info(f"Agendamento atualizado: {job['nomeAgendamento']} (ID: {job_id})")
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