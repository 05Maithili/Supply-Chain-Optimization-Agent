"""
SQLAlchemy ORM models for SupplyChainAI.
"""
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, Date, DateTime, ForeignKey, Text, Boolean, Enum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base
import enum


class RiskLevel(str, enum.Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100))
    unit_price: Mapped[float] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sales: Mapped[List["Sale"]] = relationship("Sale", back_populates="product")
    inventory: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="product")
    supplier_products: Mapped[List["SupplierProduct"]] = relationship("SupplierProduct", back_populates="product")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    warehouse_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    warehouse_name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer)
    current_utilization: Mapped[float] = mapped_column(Float, default=0.0)
    manager: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    inventory: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="warehouse")
    sales: Mapped[List["Sale"]] = relationship("Sale", back_populates="warehouse")
    shipments_from: Mapped[List["Shipment"]] = relationship("Shipment", foreign_keys="Shipment.warehouse_id", back_populates="warehouse")
    routes_from: Mapped[List["TransportRoute"]] = relationship("TransportRoute", foreign_keys="TransportRoute.origin_warehouse_id", back_populates="origin_warehouse")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    supplier_name: Mapped[str] = mapped_column(String(200))
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    reliability: Mapped[float] = mapped_column(Float)          # 0-100
    quality_score: Mapped[float] = mapped_column(Float)        # 0-100
    lead_time_days: Mapped[int] = mapped_column(Integer)
    capacity: Mapped[int] = mapped_column(Integer)
    historical_delays: Mapped[int] = mapped_column(Integer, default=0)
    order_fulfillment_rate: Mapped[float] = mapped_column(Float, default=95.0)  # %
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    supplier_products: Mapped[List["SupplierProduct"]] = relationship("SupplierProduct", back_populates="supplier")


class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[str] = mapped_column(String(20), ForeignKey("suppliers.supplier_id"))
    product_id: Mapped[str] = mapped_column(String(20), ForeignKey("products.product_id"))
    unit_cost: Mapped[float] = mapped_column(Float)
    min_order_quantity: Mapped[int] = mapped_column(Integer, default=1)
    max_order_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    discount_percent: Mapped[float] = mapped_column(Float, default=0.0)

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="supplier_products")
    product: Mapped["Product"] = relationship("Product", back_populates="supplier_products")


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[str] = mapped_column(String(20), ForeignKey("products.product_id"), index=True)
    warehouse_id: Mapped[str] = mapped_column(String(20), ForeignKey("warehouses.warehouse_id"), index=True)
    sale_date: Mapped[date] = mapped_column(Date, index=True)
    quantity_sold: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    total_revenue: Mapped[float] = mapped_column(Float)
    customer_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="sales")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="sales")


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[str] = mapped_column(String(20), ForeignKey("products.product_id"), index=True)
    warehouse_id: Mapped[str] = mapped_column(String(20), ForeignKey("warehouses.warehouse_id"), index=True)
    current_stock: Mapped[int] = mapped_column(Integer, default=0)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0)
    max_stock: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped["Product"] = relationship("Product", back_populates="inventory")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="inventory")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    segment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class TransportRoute(Base):
    __tablename__ = "transport_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    route_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    origin_warehouse_id: Mapped[str] = mapped_column(String(20), ForeignKey("warehouses.warehouse_id"))
    destination: Mapped[str] = mapped_column(String(200))
    distance_km: Mapped[float] = mapped_column(Float)
    base_cost_per_unit: Mapped[float] = mapped_column(Float)
    transit_time_days: Mapped[int] = mapped_column(Integer)
    transport_mode: Mapped[str] = mapped_column(String(50), default="Road")
    carrier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    origin_warehouse: Mapped["Warehouse"] = relationship("Warehouse", foreign_keys=[origin_warehouse_id], back_populates="routes_from")


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    shipment_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    product_id: Mapped[str] = mapped_column(String(20), ForeignKey("products.product_id"))
    warehouse_id: Mapped[str] = mapped_column(String(20), ForeignKey("warehouses.warehouse_id"))
    destination: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="Pending")
    ship_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estimated_delivery: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    transportation_cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", foreign_keys=[warehouse_id], back_populates="shipments_from")


class SupplyChainDocument(Base):
    __tablename__ = "supply_chain_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(300))
    original_filename: Mapped[str] = mapped_column(String(300))
    file_type: Mapped[str] = mapped_column(String(10))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    upload_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    num_chunks: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="Processing")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vector_store_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
