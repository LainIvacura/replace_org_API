from fastapi import FastAPI, HTTPException, Query
from supp_adel import ConnectionFactory
from enum import Enum
from config import (
    DB_ORGANIZATION, DB_CATALOG, DB_CONTRACT, DB_SECTION,
    DB_EA21, DB_EZT, DB_EOK, DB_EZK21, DB_OKB20,
    PROD, HOST, PORT,
)

app = FastAPI(title="API для замены организатора/заказчика", version="1.0")


class ChangeType(str, Enum):
    ORGANIZER = "организатор"  # замена организатора
    CUSTOMER = "заказчик"  # замена заказчика


cf = ConnectionFactory()

# Организации
connect_organization = cf.get_connection(DB_ORGANIZATION, prod=PROD)
table_organization = connect_organization.get_table('organization')

# Каталог 44
connect_44catalog = cf.get_connection(DB_CATALOG, prod=PROD)
table_44catalog = connect_44catalog.get_table('catalog_procedure')
table_44catalog_lot = connect_44catalog.get_table('catalog_procedure_lot')
table_44catalog_lot_customer = connect_44catalog.get_table('catalog_procedure_lot_customer')
table_44catalog_catalog_contract = connect_44catalog.get_table('catalog_contract')

# Контракты
connect_contract_44 = cf.get_connection(DB_CONTRACT, prod=PROD)
table_44contract = connect_contract_44.get_table('contract')

# Секции (section)
connect_sectionks = cf.get_connection(DB_SECTION)
sectionks_organization_table = connect_sectionks.get_table('organization')

# Площадки
connect_44ea21 = cf.get_connection(DB_EA21, prod=PROD)
table_44ea21_procedures = connect_44ea21.get_table('procedures')
table_44ea21_lot = connect_44ea21.get_table('lot')
table_44ea21_lotCustomer = connect_44ea21.get_table('lotCustomer')

connect_44ezt = cf.get_connection(DB_EZT, prod=PROD)
table_44ezt_procedures = connect_44ezt.get_table('procedures')
table_44ezt_lot = connect_44ezt.get_table('lot')
table_44ezt_lotCustomer = connect_44ezt.get_table('lotCustomer')

connect_44eok = cf.get_connection(DB_EOK, prod=PROD)
table_44eok_procedures = connect_44eok.get_table('procedures')
table_44eok_lot = connect_44eok.get_table('lot')
table_44eok_lotCustomer = connect_44eok.get_table('lotCustomer')

connect_44ezk21 = cf.get_connection(DB_EZK21, prod=PROD)
table_44ezk21_procedures = connect_44ezk21.get_table('procedures')
table_44ezk21_lot = connect_44ezk21.get_table('lot')
table_44ezk21_lotCustomer = connect_44ezk21.get_table('lotCustomer')

connect_44okb20 = cf.get_connection(DB_OKB20, prod=PROD)
table_44okb20_procedures = connect_44okb20.get_table('procedures')
table_44okb20_lot = connect_44okb20.get_table('lot')
table_44okb20_lotCustomer = connect_44okb20.get_table('lotCustomer')


# Эндпоинт для замены организатора/заказчика
@app.post("/replace-organization")
async def replace_organization(
        Номер_процедуры: str = Query(..., description="Номер процедуры"),
        Старый_ИНН: str = Query(..., description="Старый ИНН"),
        Новый_ИНН: str = Query(..., description="Новый ИНН"),
        Тип_замены: ChangeType = Query(...,
                                       description=" замена организатора, замена заказчика")
):
    """
    Замена организатора или заказчика в процедуре

    - **организатор**: меняет организатора процедуры (поля placer_*, customerId)
    - **заказчик**: меняет заказчика в процедуре (поля lotCustomer, contract, catalog_contract)
    """
    if not Номер_процедуры or not Номер_процедуры.strip():
        raise HTTPException(status_code=400, detail="Не указан номер процедуры")

    if not Старый_ИНН or not Старый_ИНН.strip():
        raise HTTPException(status_code=400, detail="Не указан старый ИНН")

    if not Новый_ИНН or not Новый_ИНН.strip():
        raise HTTPException(status_code=400, detail="Не указан новый ИНН")

    regNumber_IntegrationPacket = Номер_процедуры.strip()
    Old_reg = Старый_ИНН.strip()
    NewReg = Новый_ИНН.strip()

    # Преобразуем понятное название в код для логики
    if Тип_замены == ChangeType.ORGANIZER:
        Change_Type_teg = 'F'
        change_type_name = "организатор"
        org_type = 'supplier'
        org_type_sectionks = 'supplier'
    else:  # ChangeType.CUSTOMER
        Change_Type_teg = 'R'
        change_type_name = "заказчик"
        org_type = 'customer'
        org_type_sectionks = 'customer'

    try:
        # Поиск нового заказчика/организатора в sectionks
        with connect_sectionks.get_session() as sess:
            sectionks_organization_info = sess.query(sectionks_organization_table).filter(
                sectionks_organization_table.inn == NewReg,
                sectionks_organization_table.active == 1,
                sectionks_organization_table.oosRegistrationNumber != None,
                sectionks_organization_table.type == org_type_sectionks
            ).all()

        if not sectionks_organization_info:
            raise HTTPException(status_code=404, detail=f"Нет данных ИНН: {NewReg}")

        for row_organization in sectionks_organization_info:
            id_oosRegistrationNumber = row_organization.id
            guid_oosRegistrationNumber = row_organization.guid
            fullName_oosRegistrationNumber = row_organization.fullName
            shortName_oosRegistrationNumber = row_organization.shortName
            inn_oosRegistrationNumber = row_organization.inn
            kpp_oosRegistrationNumber = row_organization.kpp
            ogrn_oosRegistrationNumber = row_organization.ogrn

        # Поиск в organization.organization
        with connect_organization.get_session() as sess:
            organization_organization = sess.query(table_organization).filter(
                table_organization.externalId == id_oosRegistrationNumber,
                table_organization.active == 1,
                table_organization.dtype == org_type
            ).all()

        if not organization_organization:
            raise HTTPException(status_code=404, detail="Нет данных в organization.organization")

        for row_organization in organization_organization:
            id_organization = row_organization.id

        # Старые данные
        with connect_sectionks.get_session() as sess:
            sectionks_organization_info_Old_reg = sess.query(sectionks_organization_table).filter(
                sectionks_organization_table.inn == Old_reg,
                sectionks_organization_table.active == 1,
                sectionks_organization_table.oosRegistrationNumber != None,
                sectionks_organization_table.type == org_type_sectionks
            ).all()

        if not sectionks_organization_info_Old_reg:
            raise HTTPException(status_code=404, detail=f"Нет данных ИНН: {Old_reg}")

        for row_organization_Old_reg in sectionks_organization_info_Old_reg:
            id_oosRegistrationNumber_Old_reg = row_organization_Old_reg.id
            inn_oosRegistrationNumber_old = row_organization_Old_reg.inn

        with connect_organization.get_session() as sess:
            organization_organization_old = sess.query(table_organization).filter(
                table_organization.externalId == id_oosRegistrationNumber_Old_reg,
                table_organization.active == 1,
                table_organization.dtype == org_type
            ).all()

        if not organization_organization_old:
            raise HTTPException(status_code=404, detail="Нет данных в organization.organization для старого ИНН")

        for organization_old in organization_organization_old:
            id_organization_old = organization_old.id

        updated_tables = []

        # ЗАМЕНА ОРГАНИЗАТОРА
        if Change_Type_teg == 'F':
            connections = {
                'site_1': connect_44ea21,
                'site_2': connect_44ezt,
                'site_3': connect_44eok,
                'site_4': connect_44ezk21,
                'site_5': connect_44okb20,
            }

            found = False

            for code, conn in connections.items():
                try:
                    procedure_table = conn.get_table('procedures')
                    with conn.get_session() as sess:
                        proc_info = sess.query(procedure_table).filter(
                            procedure_table.registrationNumber == regNumber_IntegrationPacket,
                            procedure_table.active == '1'
                        ).all()

                        if proc_info:
                            found = True
                            for row in proc_info:
                                sess.query(procedure_table).filter(
                                    procedure_table.id == row.id
                                ).update({procedure_table.customerId: id_organization})
                                sess.commit()
                                updated_tables.append(f"{code}.procedures (id: {row.id})")
                            break
                except Exception as e:
                    continue

            if not found:
                raise HTTPException(status_code=404,
                                    detail=f"Нет данных по процедуре в БД 44ea21,44ezt,44eok,44ezk21,44okb20")

            # Обновляем catalog_44.catalog_procedure
            with connect_44catalog.get_session() as sess:
                connect_44catalog_info = sess.query(table_44catalog).filter(
                    table_44catalog.registration_number == regNumber_IntegrationPacket,
                    table_44catalog.deleted_at.is_(None)
                ).first()

                if not connect_44catalog_info:
                    raise HTTPException(status_code=404, detail="Нет данных в БД 44catalog")

                id_44catalog = connect_44catalog_info.id

                sess.query(table_44catalog).filter(
                    table_44catalog.id == id_44catalog
                ).update({
                    table_44catalog.placer_id: id_oosRegistrationNumber,
                    table_44catalog.placer_guid: guid_oosRegistrationNumber,
                    table_44catalog.placer_full_name: fullName_oosRegistrationNumber,
                    table_44catalog.placer_short_name: shortName_oosRegistrationNumber,
                    table_44catalog.placer_inn: inn_oosRegistrationNumber,
                    table_44catalog.placer_kpp: kpp_oosRegistrationNumber,
                    table_44catalog.placer_ogrn: ogrn_oosRegistrationNumber
                })
                sess.commit()
                updated_tables.append(f"catalog_44.catalog_procedure (id: {id_44catalog})")

        # ЗАМЕНА ЗАКАЗЧИКА
        elif Change_Type_teg == 'R':
            connections = [
                (connect_44ea21, table_44ea21_procedures, table_44ea21_lot, table_44ea21_lotCustomer),
                (connect_44ezt, table_44ezt_procedures, table_44ezt_lot, table_44ezt_lotCustomer),
                (connect_44eok, table_44eok_procedures, table_44eok_lot, table_44eok_lotCustomer),
                (connect_44ezk21, table_44ezk21_procedures, table_44ezk21_lot, table_44ezk21_lotCustomer),
                (connect_44okb20, table_44okb20_procedures, table_44okb20_lot, table_44okb20_lotCustomer)
            ]

            found = False

            for conn, table_proc, table_lot, table_customer in connections:
                with conn.get_session() as sess:
                    query = (
                        sess.query(table_customer)
                            .select_from(table_proc)
                            .join(table_lot, table_lot.procedureId == table_proc.id)
                            .join(table_customer, table_customer.lotId == table_lot.id)
                            .filter(
                            table_proc.registrationNumber == regNumber_IntegrationPacket,
                            table_proc.active == '1',
                            table_customer.organizationId == id_organization_old
                        )
                    )
                    results = query.all()

                    if results:
                        found = True
                        for row in results:
                            sess.query(table_customer).filter(
                                table_customer.id == row.id
                            ).update({table_customer.organizationId: id_organization})
                        sess.commit()
                        updated_tables.append(f"lotCustomer обновлено: {len(results)} записей")
                        break

            if not found:
                raise HTTPException(status_code=404, detail="Данные процедуры не найдены")

            # Обновляем catalog_44.catalog_procedure_lot_customer
            with connect_44catalog.get_session() as sess:
                query_44catalog_lot_customer = (
                    sess.query(table_44catalog_lot_customer)
                        .select_from(table_44catalog)
                        .outerjoin(table_44catalog_lot, table_44catalog.id == table_44catalog_lot.procedure_id)
                        .outerjoin(table_44catalog_lot_customer,
                                   table_44catalog_lot.id == table_44catalog_lot_customer.lot_id)
                        .filter(
                        table_44catalog.registration_number == regNumber_IntegrationPacket,
                        table_44catalog.deleted_at.is_(None),
                        table_44catalog.parent_id.is_(None),
                        table_44catalog_lot_customer.organization_inn == inn_oosRegistrationNumber_old
                    )
                )
                results = query_44catalog_lot_customer.all()

                if results:
                    for result in results:
                        sess.query(table_44catalog_lot_customer).filter(
                            table_44catalog_lot_customer.id == result.id
                        ).update({
                            table_44catalog_lot_customer.organization_id: id_oosRegistrationNumber,
                            table_44catalog_lot_customer.organization_guid: guid_oosRegistrationNumber,
                            table_44catalog_lot_customer.organization_full_name: fullName_oosRegistrationNumber,
                            table_44catalog_lot_customer.organization_short_name: shortName_oosRegistrationNumber,
                            table_44catalog_lot_customer.organization_inn: inn_oosRegistrationNumber,
                            table_44catalog_lot_customer.organization_kpp: kpp_oosRegistrationNumber,
                            table_44catalog_lot_customer.organization_ogrn: ogrn_oosRegistrationNumber
                        })
                    sess.commit()
                    updated_tables.append(f"catalog_procedure_lot_customer обновлено: {len(results)} записей")
                else:
                    raise HTTPException(status_code=404,
                                        detail="catalog_procedure_lot_customer Данные не найдены для обновления")

            # Обновляем contract_44.contract
            with connect_contract_44.get_session() as sess:
                info_contract_44 = sess.query(table_44contract).filter(
                    table_44contract.procedure_registration_number == regNumber_IntegrationPacket,
                    table_44contract.customer_inn == inn_oosRegistrationNumber_old,
                    table_44contract.deleted_at.is_(None),
                    table_44contract.parent_id.is_(None)
                ).order_by(table_44contract.id.desc()).first()

                if info_contract_44:
                    sess.query(table_44contract).filter(
                        table_44contract.id == info_contract_44.id
                    ).update({
                        table_44contract.customer_id: id_oosRegistrationNumber,
                        table_44contract.customer_full_name: fullName_oosRegistrationNumber,
                        table_44contract.customer_short_name: shortName_oosRegistrationNumber,
                        table_44contract.customer_inn: inn_oosRegistrationNumber,
                        table_44contract.customer_kpp: kpp_oosRegistrationNumber,
                        table_44contract.customer_ogrn: ogrn_oosRegistrationNumber,
                        table_44contract.customer_guid: guid_oosRegistrationNumber
                    })
                    sess.commit()
                    updated_tables.append(f"contract_44.contract (id: {info_contract_44.id})")
                else:
                    raise HTTPException(status_code=404, detail="Данные не найдены в contract_44.contract")

            # Обновляем catalog_44.catalog_contract
            with connect_44catalog.get_session() as sess:
                info_44catalog_contract = sess.query(table_44catalog_catalog_contract).filter(
                    table_44catalog_catalog_contract.procedure_registration_number == regNumber_IntegrationPacket,
                    table_44catalog_catalog_contract.customer_inn == inn_oosRegistrationNumber_old,
                    table_44catalog_catalog_contract.deleted_at.is_(None)
                ).order_by(table_44catalog_catalog_contract.id.desc()).first()

                if info_44catalog_contract:
                    sess.query(table_44catalog_catalog_contract).filter(
                        table_44catalog_catalog_contract.id == info_44catalog_contract.id
                    ).update({
                        table_44catalog_catalog_contract.customer_id: id_oosRegistrationNumber,
                        table_44catalog_catalog_contract.customer_full_name: fullName_oosRegistrationNumber,
                        table_44catalog_catalog_contract.customer_short_name: shortName_oosRegistrationNumber,
                        table_44catalog_catalog_contract.customer_inn: inn_oosRegistrationNumber,
                        table_44catalog_catalog_contract.customer_kpp: kpp_oosRegistrationNumber,
                        table_44catalog_catalog_contract.customer_ogrn: ogrn_oosRegistrationNumber,
                        table_44catalog_catalog_contract.customer_guid: guid_oosRegistrationNumber
                    })
                    sess.commit()
                    updated_tables.append(f"catalog_44.catalog_contract (id: {info_44catalog_contract.id})")
                else:
                    raise HTTPException(status_code=404, detail="Данные не найдены в catalog_44.catalog_contract")

        return {
            "success": True,
            "message": f"Замена {change_type_name} выполнена успешно",
            "procedure_number": regNumber_IntegrationPacket,
            "old_inn": Old_reg,
            "new_inn": NewReg,
            "change_type": change_type_name,
            "updated_tables": updated_tables
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {str(e)}")


@app.get("/")
async def root():
    return {
        "message": "API для замены организатора/заказчика в процедурах",
        "version": "1.0",
        "endpoints": {
            "POST /replace-organization": "Замена организатора или заказчика",
            "GET /health": "Проверка статуса сервиса"
        },
        "parameters": {
            "Номер_процедуры": "номер процедуры для замены",
            "Старый_ИНН": "текущий ИНН организации",
            "Новый_ИНН": "новый ИНН организации",
            "Тип_замены": "организатор или заказчик"
        },
        "example_organizer": {
            "Номер_процедуры": "11111111111111",
            "Старый_ИНН": "1111111111",
            "Новый_ИНН": "22222222222",
            "Тип_замены": "организатор"
        },
        "example_customer": {
            "Номер_процедуры": "33333333333",
            "Старый_ИНН": "4444444444",
            "Новый_ИНН": "8888888888",
            "Тип_замены": "заказчик"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)