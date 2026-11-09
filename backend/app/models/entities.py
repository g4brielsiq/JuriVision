"""
Entidades Relacionais ORM (SQLAlchemy 2.0) — Modelo Entidade-Relacionamento (MER/DER).
Rastreabilidade:
- ARCHITECTURE.md: Seção 7 (Visão de Dados — MER / DER) e ADR-003
- EAP: 1.3.1 Armazenamento (Modelo Relacional, Banco Estruturado)
- Requisitos: RF-01 a RF-09, RN-01 (Invariante de Anonimização LGPD)
"""
from datetime import date, datetime, timezone
import uuid
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Usuario(Base):
    """Entidade USUARIO: Profissional do Direito (Advogado) autenticado na plataforma."""

    __tablename__ = "usuarios"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    numero_oab: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    processos: Mapped[List["Processo"]] = relationship(
        "Processo", back_populates="usuario", cascade="all, delete-orphan"
    )


class Processo(Base):
    """
    Entidade PROCESSO: Registro processual higienizado segundo a barreira obrigatória LGPD (RN-01).
    Nenhum CPF, RG ou nome completo de pessoa física sem máscara é persistido nesta tabela.
    """

    __tablename__ = "processos"

    id_processo: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    numero_processo: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    arquivo_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    origem_ingestao: Mapped[str] = mapped_column(String(20), nullable=False, default="PDF")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PROCESSADO")
    tema: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    magistrado: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    comarca: Mapped[str] = mapped_column(String(150), nullable=False, default="1ª Vara Cível de Maceió")
    autor_anonimizado: Mapped[str] = mapped_column(String(200), nullable=False)
    reu_anonimizado: Mapped[str] = mapped_column(String(200), nullable=False)
    resumo_nlp: Mapped[str] = mapped_column(Text, nullable=False)
    resultado_historico: Mapped[str] = mapped_column(String(50), nullable=False, default="Em Analise")
    data_julgamento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    usuario: Mapped[Optional["Usuario"]] = relationship("Usuario", back_populates="processos")
    analise_preditiva: Mapped[Optional["AnalisePreditiva"]] = relationship(
        "AnalisePreditiva", back_populates="processo", uselist=False, cascade="all, delete-orphan"
    )
    logs_lgpd: Mapped[List["LogAuditoriaLGPD"]] = relationship(
        "LogAuditoriaLGPD", back_populates="processo", cascade="all, delete-orphan"
    )


class AnalisePreditiva(Base):
    """Entidade ANALISE_PREDITIVA: Parecer estatístico, prazo estimado e recomendação de tese (RF-06)."""

    __tablename__ = "analises_preditivas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    id_processo: Mapped[str] = mapped_column(
        String(64), ForeignKey("processos.id_processo", ondelete="CASCADE"), unique=True, nullable=False
    )
    probabilidade_deferimento: Mapped[float] = mapped_column(Float, nullable=False)
    margem_confianca: Mapped[float] = mapped_column(Float, nullable=False, default=0.08)
    tempo_estimado_sentenca_meses: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    casos_similares_encontrados: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tese_recomendada: Mapped[str] = mapped_column(Text, nullable=False)
    tendencia_juiz: Mapped[str] = mapped_column(Text, nullable=False)
    provedor_ia_utilizado: Mapped[str] = mapped_column(
        String(50), nullable=False, default="local_heuristic"
    )
    calculado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    processo: Mapped["Processo"] = relationship("Processo", back_populates="analise_preditiva")


class LogAuditoriaLGPD(Base):
    """Entidade LOG_AUDITORIA_LGPD: Evidência auditável de higienização local de dados sensíveis (RF-04 / RN-01)."""

    __tablename__ = "logs_auditoria_lgpd"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    id_processo: Mapped[str] = mapped_column(
        String(64), ForeignKey("processos.id_processo", ondelete="CASCADE"), nullable=False
    )
    total_cpfs_mascarados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_nomes_mascarados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    texto_higienizado_verificado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    processado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    processo: Mapped["Processo"] = relationship("Processo", back_populates="logs_lgpd")
