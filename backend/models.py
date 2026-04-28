"""
SQLAlchemy models for DID and Blog Post storage
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DIDRecord(Base):
    """Store DID records and associated metadata"""
    __tablename__ = "did_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    did = Column(String(255), unique=True, nullable=False, index=True)
    address = Column(String(42), unique=True, nullable=False, index=True)
    public_key = Column(Text, nullable=False)
    display_name = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)
    did_document = Column(Text, nullable=False)  # JSON serialized
    tx_hash = Column(String(66), nullable=True)
    block_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    blog_posts = relationship("BlogPost", back_populates="author_record")

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "did": self.did,
            "address": self.address,
            "public_key": self.public_key,
            "display_name": self.display_name,
            "bio": self.bio,
            "did_document": self.did_document,
            "tx_hash": self.tx_hash,
            "block_number": self.block_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active
        }


class BlogPost(Base):
    """Store blog posts with signature verification"""
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    author_did = Column(String(255), ForeignKey("did_records.did"), nullable=False, index=True)
    author_address = Column(String(42), nullable=False, index=True)
    content_hash = Column(String(66), nullable=False, index=True)
    signature = Column(Text, nullable=False)
    tags = Column(String(500), nullable=True)  # comma-separated
    tx_hash = Column(String(66), nullable=True)
    block_number = Column(Integer, nullable=True)
    chain_verified = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    author_record = relationship("DIDRecord", back_populates="blog_posts")

    # Indexes
    __table_args__ = (
        Index("idx_author_published", "author_address", "published_at"),
        Index("idx_published_at", "published_at"),
    )

    def to_dict(self, include_author=False):
        """Convert to dictionary"""
        data = {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "author_did": self.author_did,
            "author_address": self.author_address,
            "content_hash": self.content_hash,
            "signature": self.signature,
            "tags": self.tags.split(",") if self.tags else [],
            "tx_hash": self.tx_hash,
            "block_number": self.block_number,
            "chain_verified": self.chain_verified,
            "published_at": self.published_at.isoformat() if self.published_at else None
        }

        if include_author and self.author_record:
            data["author"] = self.author_record.to_dict()

        return data


def init_db(engine):
    """Initialize database tables"""
    Base.metadata.create_all(engine)
