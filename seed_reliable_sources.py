import sqlite3
import os
import sys

# Add root to path
sys.path.append(os.getcwd())
from backend.db.queries import get_db

RELIABLE_SOURCES = [
    # OEMs (1-35)
    {"name": "Tata Motors", "url": "https://twitter.com/TataMotors", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "IN"},
    {"name": "Mahindra Electric", "url": "https://twitter.com/MahindraRise", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.87, "access_method": "Playwright", "country": "IN"},
    {"name": "Ola Electric", "url": "https://twitter.com/OlaElectric", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Ather Energy", "url": "https://twitter.com/atherenergy", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "TVS Motor", "url": "https://twitter.com/TVSMotorCompany", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.83, "access_method": "Playwright", "country": "IN"},
    {"name": "Bajaj Auto", "url": "https://twitter.com/bajaj_auto", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.82, "access_method": "Playwright", "country": "IN"},
    {"name": "MG Motor India", "url": "https://twitter.com/MGMotorIn", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.84, "access_method": "Playwright", "country": "IN"},
    {"name": "Hyundai India", "url": "https://twitter.com/HyundaiIndia", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.83, "access_method": "Playwright", "country": "IN"},
    {"name": "BYD India", "url": "https://twitter.com/BYD_India", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.82, "access_method": "Playwright", "country": "IN"},
    {"name": "Kia India", "url": "https://twitter.com/KiaInd", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.80, "access_method": "Playwright", "country": "IN"},
    {"name": "Simple Energy", "url": "https://twitter.com/simpleenergy", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.82, "access_method": "Playwright", "country": "IN"},
    {"name": "Ultraviolette Automotive", "url": "https://twitter.com/UltravioletteEV", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.84, "access_method": "Playwright", "country": "IN"},
    {"name": "Hero Vida", "url": "https://twitter.com/VidaDotWorld", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.83, "access_method": "Playwright", "country": "IN"},
    {"name": "Hop Electric", "url": "https://twitter.com/Hopelectric_", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Ampere", "url": "https://twitter.com/ampere_ebikes", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.80, "access_method": "Playwright", "country": "IN"},
    {"name": "Revolt Motors", "url": "https://twitter.com/RevoltMotorsIN", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.81, "access_method": "Playwright", "country": "IN"},
    {"name": "Okinawa Autotech", "url": "https://twitter.com/OkinawaAutotech", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.79, "access_method": "Playwright", "country": "IN"},
    {"name": "Pure EV", "url": "https://twitter.com/PUREEVIndia", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.77, "access_method": "Playwright", "country": "IN"},
    {"name": "Tork Motors", "url": "https://twitter.com/torkmotors", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.80, "access_method": "Playwright", "country": "IN"},
    {"name": "Greaves Cotton", "url": "https://twitter.com/GreavesCottonLtd", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.82, "access_method": "Playwright", "country": "IN"},
    {"name": "Atul Auto", "url": "https://twitter.com/AtulAutoLimited", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Kinetic Green", "url": "https://twitter.com/KineticGreenIN", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.79, "access_method": "Playwright", "country": "IN"},
    {"name": "Altigreen Propulsion", "url": "https://twitter.com/Altigreen", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.81, "access_method": "Playwright", "country": "IN"},
    {"name": "Omega Seiki Mobility", "url": "https://twitter.com/OmegaSeiki", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.80, "access_method": "Playwright", "country": "IN"},
    {"name": "Euler Motors", "url": "https://twitter.com/EulerMotors", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.82, "access_method": "Playwright", "country": "IN"},
    {"name": "Piaggio India", "url": "https://twitter.com/PiaggioIndia", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.83, "access_method": "Playwright", "country": "IN"},
    {"name": "Switch Mobility", "url": "https://twitter.com/switch_mobility", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "JBM Auto", "url": "https://twitter.com/jbm_group", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.82, "access_method": "Playwright", "country": "IN"},
    {"name": "Olectra Greentech", "url": "https://twitter.com/OlectraGreen", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.83, "access_method": "Playwright", "country": "IN"},
    {"name": "VE Commercial (Eicher)", "url": "https://twitter.com/VECommercial", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.84, "access_method": "Playwright", "country": "IN"},
    {"name": "BharatBenz India", "url": "https://twitter.com/BharatBenz1", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.84, "access_method": "Playwright", "country": "IN"},
    {"name": "Eka Mobility", "url": "https://twitter.com/ekamobility", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.81, "access_method": "Playwright", "country": "IN"},
    {"name": "River", "url": "https://twitter.com/ridewithriver", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Matter Energy", "url": "https://twitter.com/matter_energy", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.79, "access_method": "Playwright", "country": "IN"},
    {"name": "Orxa Energies", "url": "https://twitter.com/OrxaEnergies", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 2", "score_authority": 0.77, "access_method": "Playwright", "country": "IN"},
    {"name": "Tesla", "url": "https://twitter.com/Tesla", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.92, "access_method": "Playwright", "country": "Global"},
    {"name": "BYD Global", "url": "https://twitter.com/BYDCompany", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "Global"},
    {"name": "Volkswagen", "url": "https://twitter.com/Volkswagen", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.87, "access_method": "Playwright", "country": "Global"},
    {"name": "Ford", "url": "https://twitter.com/Ford", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "Global"},
    {"name": "GM", "url": "https://twitter.com/GM", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "Global"},
    {"name": "Hyundai Global", "url": "https://twitter.com/Hyundai_Global", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.87, "access_method": "Playwright", "country": "Global"},
    {"name": "Rivian", "url": "https://twitter.com/Rivian", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.90, "access_method": "Playwright", "country": "Global"},
    {"name": "Lucid Motors", "url": "https://twitter.com/LucidMotors", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.89, "access_method": "Playwright", "country": "Global"},
    {"name": "Polestar", "url": "https://twitter.com/PolestarCars", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "Global"},
    {"name": "NIO", "url": "https://twitter.com/NIOGlobal", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.87, "access_method": "Playwright", "country": "Global"},
    {"name": "Xpeng", "url": "https://twitter.com/XPengMotors", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.86, "access_method": "Playwright", "country": "Global"},
    {"name": "Li Auto", "url": "https://twitter.com/LiAuto_Official", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "Global"},
    {"name": "Rimac Automobili", "url": "https://twitter.com/RimacAuto", "type": "OEM", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "Global"},

    # CPOs (49-73)
    {"name": "Tata Power EZ Charge", "url": "https://twitter.com/TataPower", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.86, "access_method": "Playwright", "country": "IN"},
    {"name": "Statiq", "url": "https://twitter.com/StatiqIndia", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.84, "access_method": "Playwright", "country": "IN"},
    {"name": "ChargeZone", "url": "https://twitter.com/ChargeZone_", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.84, "access_method": "Playwright", "country": "IN"},
    {"name": "Zeon Charging", "url": "https://twitter.com/zeoncharging", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.83, "access_method": "Playwright", "country": "IN"},
    {"name": "Jio-bp Pulse", "url": "https://twitter.com/jiobp", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Fortum India", "url": "https://twitter.com/FortumIndia", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.82, "access_method": "Playwright", "country": "IN"},
    {"name": "GLIDA India", "url": "https://twitter.com/GlidaIndia", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Magenta ChargeGrid", "url": "https://twitter.com/MagentaCharge", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.84, "access_method": "Playwright", "country": "IN"},
    {"name": "EV Motors PlugNgo", "url": "https://twitter.com/PlugNgoIndia", "type": "CPO", "category": "Charging_Network", "tier": "Tier 2", "score_authority": 0.80, "access_method": "Playwright", "country": "IN"},
    {"name": "Delta Electronics India", "url": "https://twitter.com/DeltaIndia", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.86, "access_method": "Playwright", "country": "IN"},
    {"name": "Exicom Power", "url": "https://twitter.com/ExicomIndia", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "ABB India EV", "url": "https://twitter.com/ABBIndia", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.87, "access_method": "Playwright", "country": "IN"},
    {"name": "Siemens India eMobility", "url": "https://twitter.com/SiemensIndia", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.86, "access_method": "Playwright", "country": "IN"},
    {"name": "Servotech Power Systems", "url": "https://twitter.com/Servotech_Ltd", "type": "CPO", "category": "Charging_Network", "tier": "Tier 2", "score_authority": 0.81, "access_method": "Playwright", "country": "IN"},
    {"name": "Sun Mobility", "url": "https://twitter.com/SUN_Mobility", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "IN"},
    {"name": "Battery Smart", "url": "https://twitter.com/Battery_Smart", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.86, "access_method": "Playwright", "country": "IN"},
    {"name": "Bolt.earth", "url": "https://twitter.com/BoltEarth", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Kazam EV", "url": "https://twitter.com/KazamEV", "type": "CPO", "category": "Charging_Network", "tier": "Tier 2", "score_authority": 0.82, "access_method": "Playwright", "country": "IN"},
    {"name": "ChargePoint", "url": "https://twitter.com/ChargePointnet", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.92, "access_method": "Playwright", "country": "Global"},
    {"name": "EVBox", "url": "https://twitter.com/EVBox", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.89, "access_method": "Playwright", "country": "Global"},
    {"name": "Electrify America", "url": "https://twitter.com/ElectrifyAm", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.91, "access_method": "Playwright", "country": "Global"},
    {"name": "Ionity", "url": "https://twitter.com/IONITY_EU", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.90, "access_method": "Playwright", "country": "Global"},
    {"name": "Tesla Supercharger", "url": "https://twitter.com/TeslaCharging", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.95, "access_method": "Playwright", "country": "Global"},
    {"name": "Shell Recharge", "url": "https://twitter.com/ShellRecharge", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "Global"},
    {"name": "BP Pulse", "url": "https://twitter.com/bp_pulse", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "Global"},

    # Government (74-83)
    {"name": "PIB India", "url": "https://twitter.com/PIB_India", "type": "Government", "category": "Policy_and_Infrastructure", "tier": "Tier 1", "score_authority": 0.92, "access_method": "Playwright", "country": "IN"},
    {"name": "MoHI India", "url": "https://twitter.com/MoHI_India", "type": "Government", "category": "Policy_and_Infrastructure", "tier": "Tier 1", "score_authority": 0.90, "access_method": "Playwright", "country": "IN"},
    {"name": "NITI Aayog", "url": "https://twitter.com/NITIAayog", "type": "Government", "category": "Policy_and_Infrastructure", "tier": "Tier 1", "score_authority": 0.90, "access_method": "Playwright", "country": "IN"},
    {"name": "BEE India", "url": "https://twitter.com/beeindiadigital", "type": "Government", "category": "Policy_and_Infrastructure", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "IN"},
    {"name": "CESL India", "url": "https://twitter.com/CESLIndia", "type": "Government", "category": "Policy_and_Infrastructure", "tier": "Tier 1", "score_authority": 0.87, "access_method": "Playwright", "country": "IN"},
    {"name": "SIAM India", "url": "https://twitter.com/siamindia", "type": "Government", "category": "Policy_and_Infrastructure", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "SMEV India", "url": "https://twitter.com/smevindia", "type": "Government", "category": "Policy_and_Infrastructure", "tier": "Tier 1", "score_authority": 0.86, "access_method": "Playwright", "country": "IN"},
    {"name": "FADA India", "url": "https://twitter.com/FADA_India", "type": "Government", "category": "Policy_and_Infrastructure", "tier": "Tier 1", "score_authority": 0.84, "access_method": "Playwright", "country": "IN"},
    {"name": "ARAI India", "url": "https://twitter.com/ARAIIndia", "type": "Government", "category": "Policy_and_Infrastructure", "tier": "Tier 1", "score_authority": 0.92, "access_method": "Playwright", "country": "IN"},
    {"name": "ICAT Manesar", "url": "https://twitter.com/ICAT_Manesar", "type": "Government", "category": "Policy_and_Infrastructure", "tier": "Tier 1", "score_authority": 0.90, "access_method": "Playwright", "country": "IN"},

    # Media (84-99)
    {"name": "Electrek", "url": "https://electrek.co/feed/", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.94, "access_method": "Playwright", "country": "Global"},
    {"name": "InsideEVs", "url": "https://insideevs.com/rss/articles/all/", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.93, "access_method": "Playwright", "country": "Global"},
    {"name": "CleanTechnica", "url": "https://cleantechnica.com/feed/", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.92, "access_method": "Playwright", "country": "Global"},
    {"name": "EV Magazine", "url": "https://twitter.com/EV_Mag", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "Global"},
    {"name": "Green Car Reports", "url": "https://www.greencarreports.com/rss", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.91, "access_method": "Playwright", "country": "Global"},
    {"name": "Teslarati", "url": "https://twitter.com/Teslarati", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.90, "access_method": "Playwright", "country": "Global"},
    {"name": "EVreporter India", "url": "https://twitter.com/evreporter", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "IN"},
    {"name": "EVreporter RSS", "url": "https://evreporter.com/feed/", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "IN"},
    {"name": "PlugIn India", "url": "https://twitter.com/pluginindia", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.87, "access_method": "Playwright", "country": "IN"},
    {"name": "ET Auto India", "url": "https://twitter.com/ETAuto", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.90, "access_method": "Playwright", "country": "IN"},
    {"name": "Autocar India", "url": "https://twitter.com/autocarindiamag", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.92, "access_method": "Playwright", "country": "IN"},
    {"name": "Overdrive India", "url": "https://twitter.com/odmag", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "IN"},
    {"name": "Saur Energy", "url": "https://twitter.com/Saur_Energy", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.82, "access_method": "Playwright", "country": "IN"},
    {"name": "Saur Energy RSS", "url": "https://www.saurenergy.com/solar-energy-news/", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.82, "access_method": "Playwright", "country": "IN"},
    {"name": "Mercom India EV", "url": "https://mercomindia.com/feed/", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.89, "access_method": "Playwright", "country": "IN"},
    {"name": "CleanTechnica India RSS", "url": "https://cleantechnica.com/tag/india/feed/", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.92, "access_method": "Playwright", "country": "IN"},
    {"name": "Inc42 Mobility", "url": "https://twitter.com/Inc42", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Times of India EV", "url": "https://timesofindia.indiatimes.com/auto/ev", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.92, "access_method": "Playwright", "country": "IN"},
    {"name": "Hindustan Times Auto", "url": "https://auto.hindustantimes.com/ev", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.91, "access_method": "Playwright", "country": "IN"},
    {"name": "Business Standard EV", "url": "https://www.business-standard.com/topic/electric-vehicles", "type": "Media", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.87, "access_method": "Playwright", "country": "IN"},

    # Components (100-105)
    {"name": "CATL Global", "url": "https://twitter.com/catl_official", "type": "Components", "category": "Battery_Manufacturer", "tier": "Tier 1", "score_authority": 0.92, "access_method": "Playwright", "country": "Global"},
    {"name": "LG Energy Solution", "url": "https://twitter.com/LG_EnergySol", "type": "Components", "category": "Battery_Manufacturer", "tier": "Tier 1", "score_authority": 0.90, "access_method": "Playwright", "country": "Global"},
    {"name": "Samsung SDI", "url": "https://twitter.com/SamsungSDI", "type": "Components", "category": "Battery_Manufacturer", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "Global"},
    {"name": "Panasonic Energy", "url": "https://twitter.com/Panasonic_En", "type": "Components", "category": "Battery_Manufacturer", "tier": "Tier 1", "score_authority": 0.89, "access_method": "Playwright", "country": "Global"},
    {"name": "Log9 Materials", "url": "https://twitter.com/log9materials", "type": "Components", "category": "Battery_Manufacturer", "tier": "Tier 1", "score_authority": 0.88, "access_method": "Playwright", "country": "IN"},
    {"name": "Lohum Lithium", "url": "https://twitter.com/LohumLithium", "type": "Components", "category": "Battery_Manufacturer", "tier": "Tier 1", "score_authority": 0.87, "access_method": "Playwright", "country": "IN"},

    # Video & Social (106-110)
    {"name": "Autocar India YT", "url": "https://www.youtube.com/@autocarindia1", "type": "Video", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.93, "access_method": "JSON API", "country": "IN"},
    {"name": "r/IndiaEV", "url": "https://www.reddit.com/r/IndiaEV/", "type": "Social", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.75, "access_method": "JSON API", "country": "IN"},
    {"name": "r/electricvehicles", "url": "https://www.reddit.com/r/electricvehicles/", "type": "Social", "category": "EV_News", "tier": "Tier 1", "score_authority": 0.70, "access_method": "JSON API", "country": "Global"},
    {"name": "Nitin Gadkari", "url": "https://twitter.com/nitin_gadkari", "type": "Social", "category": "Policy_and_Infrastructure", "tier": "Tier 1", "score_authority": 0.96, "access_method": "Playwright", "country": "IN"},
    {"name": "Bhavish Aggarwal", "url": "https://twitter.com/bhash", "type": "Social", "category": "Passenger_EV", "tier": "Tier 1", "score_authority": 0.92, "access_method": "Playwright", "country": "IN"},

    # New Micromobility, Delivery, & OEMs (111-128)
    {"name": "Yulu Mobility Nodes", "url": "https://www.yulu.bike", "type": "OEM", "category": "Micromobility", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Zypp Electric Delivery", "url": "https://www.zypp.app", "type": "OEM", "category": "Commercial_Fleet", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Baaz Bikes Network", "url": "https://www.baazbikes.com", "type": "OEM", "category": "Two_Wheeler", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Zen Mobility Cargo", "url": "https://zenmobility.com", "type": "OEM", "category": "Three_Wheeler", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Dispatch Vehicles", "url": "https://dispatchvehicles.com", "type": "OEM", "category": "Two_Wheeler", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Turno EV Market", "url": "https://www.turno.club", "type": "CPO_Finance", "category": "Fleet_Analytics", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Vidyut Tech Finance", "url": "https://www.vidyuttech.com", "type": "CPO_Finance", "category": "Battery_Finance", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Mufin Green Finance", "url": "https://mufingreenfinance.com", "type": "CPO_Finance", "category": "Green_Capital", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Ecofy Green Mobility", "url": "https://www.ecofy.co.in", "type": "CPO_Finance", "category": "Retail_Finance", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Liger Mobility Tech", "url": "https://www.ligermobility.com", "type": "OEM", "category": "Two_Wheeler", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Geliose Mobility IITD", "url": "https://www.geliose.com", "type": "OEM", "category": "Two_Wheeler", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Gogoro India Network", "url": "https://www.gogoro.com/in", "type": "OEM_CPO", "category": "Battery_Swapping", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Strikeco Electric 3W", "url": "https://strikeco.in", "type": "OEM", "category": "Three_Wheeler", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Triton EV India", "url": "https://www.tritonev.co", "type": "OEM", "category": "Commercial_CV", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Srivaru Motors Prana", "url": "https://srivarumotors.com", "type": "OEM", "category": "Two_Wheeler", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Corrit Electric", "url": "https://corritelectric.com", "type": "OEM", "category": "Two_Wheeler", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Evtric Motors India", "url": "https://evtric.com", "type": "OEM", "category": "Two_Wheeler", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Aarya Automobiles", "url": "https://aaryaclub.com", "type": "OEM", "category": "Two_Wheeler", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},

    # New Components & Supply Chain (129-135)
    {"name": "Tata AutoComp Taco", "url": "https://www.tataautocomp.com", "type": "Components", "category": "Powertrain_Pack", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Epsilon Materials", "url": "https://www.epsilonam.com", "type": "Components", "category": "Anode_Chemistry", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Altmin Materials", "url": "https://altmin.co", "type": "Components", "category": "Cathode_LFP", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Himadri Chemicals", "url": "https://www.gohimadri.com", "type": "Components", "category": "Raw_Materials", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Bharat Forge EV", "url": "https://www.bharatforge.com", "type": "Components", "category": "Chassis_Motor", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Batx Recycling", "url": "https://batxenergies.com", "type": "Components", "category": "Battery_Recycle", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Nexcharge Exide JV", "url": "https://www.nexcharge.in", "type": "Components", "category": "Cell_Assembly", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},

    # New CPOs & Grid Operators (136-141)
    {"name": "Adani Total eMobility", "url": "https://www.adanitotalenergies.com", "type": "CPO", "category": "Charging_Network", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "BPCL eDrive Corridors", "url": "https://www.bharatpetroleum.in", "type": "CPO", "category": "Highway_CPO", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "HPCL EV Zones", "url": "https://www.hindustanpetroleum.com", "type": "CPO", "category": "Highway_CPO", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "IOCL Wayside Charging", "url": "https://www.iocl.com", "type": "CPO", "category": "Highway_CPO", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "GMR Green Transit", "url": "https://www.gmrgroup.in", "type": "CPO", "category": "Transit_Hubs", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Powergrid EV Charging", "url": "https://www.powergrid.in", "type": "CPO", "category": "Grid_Charging", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},

    # New Government & Policy Research (142-147)
    {"name": "TERI India Mobility", "url": "https://www.teriin.org", "type": "Government", "category": "Policy_Research", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "CSTEP Clean Mobility", "url": "https://www.cstep.in", "type": "Government", "category": "Grid_Integration", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "CSE India Advocacy", "url": "https://www.cseindia.org", "type": "Government", "category": "Compliance", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "BIS Standards EV", "url": "https://www.bis.gov.in", "type": "Government", "category": "Regulation", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Invest India EV", "url": "https://www.investindia.gov.in", "type": "Government", "category": "Investment_FDI", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "ACMA India Localized", "url": "https://www.acma.in", "type": "Government", "category": "Supply_Chain", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},

    # New Media & Trade Journals (148-154)
    {"name": "EV Update Media India", "url": "https://evupdatemedia.com", "type": "Media", "category": "Trade_Journal", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Auto Punditz Metrics", "url": "https://www.autopunditz.com", "type": "Media", "category": "Sales_Analytics", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Autotech Review India", "url": "https://autotechreview.com", "type": "Media", "category": "Engineering", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Power Trans India", "url": "https://www.powertransmission.in", "type": "Media", "category": "Grid_Infrastructure", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "EQ International EV", "url": "https://www.eqmagpro.com", "type": "Media", "category": "Energy_Business", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "Solar Quarter EV", "url": "https://solarquarter.com", "type": "Media", "category": "Energy_Business", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "Energetica India EV", "url": "https://www.energeticaindia.net", "type": "Media", "category": "Engineering", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},

    # New Public Transit operators (155-160)
    {"name": "BEST Bus Mumbai", "url": "https://www.bestundertaking.com", "type": "Gov/Transit", "category": "Public_Transit", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "DTC Delhi eBuses", "url": "https://dtc.delhi.gov.in", "type": "Gov/Transit", "category": "Public_Transit", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "PMPML eBus Pune", "url": "https://www.pmpml.org", "type": "Gov/Transit", "category": "Public_Transit", "tier": "Tier 2", "score_authority": 0.78, "access_method": "Playwright", "country": "IN"},
    {"name": "MSRTC Shivai Fleet", "url": "https://www.msrtc.maharashtra.gov.in", "type": "Gov/Transit", "category": "Public_Transit", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "KSRTC EV Bus Karnataka", "url": "https://ksrtc.karnataka.gov.in", "type": "Gov/Transit", "category": "Public_Transit", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"},
    {"name": "TSRTC EV Bus Telangana", "url": "https://www.tsrtc.telangana.gov.in", "type": "Gov/Transit", "category": "Public_Transit", "tier": "Tier 1", "score_authority": 0.85, "access_method": "Playwright", "country": "IN"}
]

def seed():
    from backend.db.queries import init_db
    init_db()
    print(f"Seeding reliable RSS & Web/Social sources ({len(RELIABLE_SOURCES)} Registry)...")
    with get_db() as conn:
        cur = conn.cursor()
        
        # Hard Purging / Truncating Table
        cur.execute("DELETE FROM sources")
        print("Cleaned existing sources (Truncated sources registry).")
        
        # Safe table creation for source_scores if it exists as another table in standard models
        try:
            cur.execute("CREATE TABLE IF NOT EXISTS source_scores AS SELECT * FROM sources WHERE 1=0")
        except:
            pass
            
        try:
            cur.execute("DELETE FROM source_scores")
        except:
            pass
 
        # Populate fresh registry
        for s in RELIABLE_SOURCES:
            source_id = s["name"].lower().replace(" ", "_")
            cur.execute('''
                INSERT INTO sources (
                    source_id, name, domain, type, category, tier, 
                    score_authority, activity_status, country, access_method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
            ''', (
                source_id, s["name"], s["url"], s["type"], s["category"], s["tier"],
                s["score_authority"], s["country"], s["access_method"]
            ))
            
            # Also populate source_scores for trace continuity/backward compatibility
            try:
                cur.execute('''
                    INSERT INTO source_scores (
                        source_id, name, domain, type, category, tier, 
                        score_authority, activity_status, country, access_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                ''', (
                    source_id, s["name"], s["url"], s["type"], s["category"], s["tier"],
                    s["score_authority"], s["country"], s["access_method"]
                ))
            except Exception as e:
                pass
                
        conn.commit()
    print(f"Seeding complete. {len(RELIABLE_SOURCES)} sources inserted successfully.")

if __name__ == "__main__":
    seed()
