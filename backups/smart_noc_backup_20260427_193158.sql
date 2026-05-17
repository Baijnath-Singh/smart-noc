--
-- PostgreSQL database dump
--

\restrict I8R2nJoN1JJGd1u93owDXwsELHPgh23QogtNg2SaikH86IeboVrT6DJRMIJ9WsN

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: calculate_incident_duration(); Type: FUNCTION; Schema: public; Owner: noc_admin
--

CREATE FUNCTION public.calculate_incident_duration() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.end_time IS NOT NULL AND OLD.end_time IS NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.end_time - NEW.start_time))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.calculate_incident_duration() OWNER TO noc_admin;

--
-- Name: log_incident_status_change(); Type: FUNCTION; Schema: public; Owner: noc_admin
--

CREATE FUNCTION public.log_incident_status_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.status != OLD.status THEN
        INSERT INTO incident_timeline (incident_id, event_type, description, previous_status, new_status)
        VALUES (
            NEW.id,
            'STATUS_CHANGED',
            'Incident status changed from ' || OLD.status || ' to ' || NEW.status,
            OLD.status,
            NEW.status
        );
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.log_incident_status_change() OWNER TO noc_admin;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: noc_admin
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO noc_admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: incidents; Type: TABLE; Schema: public; Owner: noc_admin
--

CREATE TABLE public.incidents (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    incident_number integer NOT NULL,
    incident_type character varying(100) NOT NULL,
    severity character varying(20) NOT NULL,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    affected_device_count integer DEFAULT 0 NOT NULL,
    affected_devices jsonb DEFAULT '[]'::jsonb NOT NULL,
    primary_device character varying(255),
    anomaly_count integer DEFAULT 0 NOT NULL,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone,
    duration_seconds integer,
    correlation_method character varying(50) NOT NULL,
    correlation_confidence numeric(5,2),
    impact_score numeric(5,2),
    root_cause text,
    remediation_plan text,
    incident_metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    resolved_at timestamp without time zone,
    root_cause_confidence numeric(5,2),
    diagnosis_timestamp timestamp without time zone,
    llm_model character varying(50),
    diagnosis_metadata jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT incidents_root_cause_confidence_check CHECK (((root_cause_confidence >= (0)::numeric) AND (root_cause_confidence <= (1)::numeric))),
    CONSTRAINT incidents_severity_check CHECK (((severity)::text = ANY ((ARRAY['LOW'::character varying, 'MEDIUM'::character varying, 'HIGH'::character varying, 'CRITICAL'::character varying])::text[]))),
    CONSTRAINT incidents_status_check CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INVESTIGATING'::character varying, 'RESOLVED'::character varying, 'CLOSED'::character varying])::text[])))
);


ALTER TABLE public.incidents OWNER TO noc_admin;

--
-- Name: COLUMN incidents.root_cause; Type: COMMENT; Schema: public; Owner: noc_admin
--

COMMENT ON COLUMN public.incidents.root_cause IS 'LLM-generated root cause analysis';


--
-- Name: COLUMN incidents.remediation_plan; Type: COMMENT; Schema: public; Owner: noc_admin
--

COMMENT ON COLUMN public.incidents.remediation_plan IS 'Array of remediation steps with priorities';


--
-- Name: COLUMN incidents.root_cause_confidence; Type: COMMENT; Schema: public; Owner: noc_admin
--

COMMENT ON COLUMN public.incidents.root_cause_confidence IS 'Confidence score 0.0-1.0 for diagnosis accuracy';


--
-- Name: COLUMN incidents.diagnosis_timestamp; Type: COMMENT; Schema: public; Owner: noc_admin
--

COMMENT ON COLUMN public.incidents.diagnosis_timestamp IS 'Timestamp when diagnosis was completed';


--
-- Name: COLUMN incidents.llm_model; Type: COMMENT; Schema: public; Owner: noc_admin
--

COMMENT ON COLUMN public.incidents.llm_model IS 'LLM model used (e.g., gpt-4, claude-3)';


--
-- Name: COLUMN incidents.diagnosis_metadata; Type: COMMENT; Schema: public; Owner: noc_admin
--

COMMENT ON COLUMN public.incidents.diagnosis_metadata IS 'Additional diagnosis metadata (tokens, duration, etc)';


--
-- Name: active_incidents; Type: VIEW; Schema: public; Owner: noc_admin
--

CREATE VIEW public.active_incidents AS
 SELECT id,
    incident_number,
    incident_type,
    severity,
    status,
    affected_device_count,
    anomaly_count,
    start_time,
    (EXTRACT(epoch FROM (now() - (start_time)::timestamp with time zone)))::integer AS age_seconds,
    primary_device,
    correlation_method
   FROM public.incidents i
  WHERE ((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INVESTIGATING'::character varying])::text[]))
  ORDER BY severity DESC, start_time DESC;


ALTER VIEW public.active_incidents OWNER TO noc_admin;

--
-- Name: diagnosis_statistics; Type: VIEW; Schema: public; Owner: noc_admin
--

CREATE VIEW public.diagnosis_statistics AS
 SELECT count(*) AS total_incidents,
    count(root_cause) AS diagnosed_incidents,
    count(*) FILTER (WHERE (root_cause IS NULL)) AS pending_diagnosis,
    count(*) FILTER (WHERE (root_cause_confidence >= 0.8)) AS high_confidence_diagnosis,
    count(*) FILTER (WHERE ((root_cause_confidence >= 0.5) AND (root_cause_confidence <= 0.8))) AS medium_confidence_diagnosis,
    count(*) FILTER (WHERE (root_cause_confidence < 0.5)) AS low_confidence_diagnosis,
    avg(root_cause_confidence) AS avg_confidence,
    avg(EXTRACT(epoch FROM (diagnosis_timestamp - created_at))) AS avg_diagnosis_delay_seconds,
    count(DISTINCT llm_model) AS models_used
   FROM public.incidents
  WHERE (created_at >= (now() - '24:00:00'::interval));


ALTER VIEW public.diagnosis_statistics OWNER TO noc_admin;

--
-- Name: VIEW diagnosis_statistics; Type: COMMENT; Schema: public; Owner: noc_admin
--

COMMENT ON VIEW public.diagnosis_statistics IS 'Real-time diagnosis performance metrics (24h rolling window)';


--
-- Name: incident_anomalies; Type: TABLE; Schema: public; Owner: noc_admin
--

CREATE TABLE public.incident_anomalies (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    incident_id uuid NOT NULL,
    anomaly_id character varying(255) NOT NULL,
    device_id character varying(255) NOT NULL,
    anomaly_type character varying(100) NOT NULL,
    detection_method character varying(50) NOT NULL,
    confidence numeric(5,2),
    "timestamp" timestamp without time zone NOT NULL,
    anomaly_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.incident_anomalies OWNER TO noc_admin;

--
-- Name: incident_diagnosis_history; Type: TABLE; Schema: public; Owner: noc_admin
--

CREATE TABLE public.incident_diagnosis_history (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    incident_id uuid NOT NULL,
    diagnosis_version integer DEFAULT 1 NOT NULL,
    root_cause text NOT NULL,
    root_cause_confidence numeric(5,2) NOT NULL,
    remediation_plan jsonb NOT NULL,
    llm_model character varying(50) NOT NULL,
    llm_prompt text,
    llm_response text,
    tokens_used integer,
    diagnosis_duration_ms integer,
    diagnosis_metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.incident_diagnosis_history OWNER TO noc_admin;

--
-- Name: TABLE incident_diagnosis_history; Type: COMMENT; Schema: public; Owner: noc_admin
--

COMMENT ON TABLE public.incident_diagnosis_history IS 'Audit trail for all diagnosis attempts including failed ones';


--
-- Name: incident_statistics; Type: VIEW; Schema: public; Owner: noc_admin
--

CREATE VIEW public.incident_statistics AS
 SELECT incident_type,
    severity,
    status,
    count(*) AS total_count,
    avg(affected_device_count) AS avg_devices_affected,
    avg(anomaly_count) AS avg_anomalies_per_incident,
    avg(duration_seconds) AS avg_duration_seconds,
    min(start_time) AS first_occurrence,
    max(start_time) AS last_occurrence
   FROM public.incidents
  GROUP BY incident_type, severity, status;


ALTER VIEW public.incident_statistics OWNER TO noc_admin;

--
-- Name: incident_timeline; Type: TABLE; Schema: public; Owner: noc_admin
--

CREATE TABLE public.incident_timeline (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    incident_id uuid NOT NULL,
    event_type character varying(50) NOT NULL,
    description text NOT NULL,
    previous_status character varying(20),
    new_status character varying(20),
    changed_by character varying(100) DEFAULT 'SYSTEM'::character varying,
    event_metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.incident_timeline OWNER TO noc_admin;

--
-- Name: incident_type_definitions; Type: TABLE; Schema: public; Owner: noc_admin
--

CREATE TABLE public.incident_type_definitions (
    incident_type character varying(100) NOT NULL,
    description text NOT NULL,
    typical_symptoms text,
    recommended_actions text
);


ALTER TABLE public.incident_type_definitions OWNER TO noc_admin;

--
-- Name: incidents_incident_number_seq; Type: SEQUENCE; Schema: public; Owner: noc_admin
--

CREATE SEQUENCE public.incidents_incident_number_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.incidents_incident_number_seq OWNER TO noc_admin;

--
-- Name: incidents_incident_number_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: noc_admin
--

ALTER SEQUENCE public.incidents_incident_number_seq OWNED BY public.incidents.incident_number;


--
-- Name: incidents_with_diagnosis; Type: VIEW; Schema: public; Owner: noc_admin
--

CREATE VIEW public.incidents_with_diagnosis AS
 SELECT id,
    incident_number,
    incident_type,
    severity,
    status,
    affected_device_count,
    affected_devices,
    primary_device,
    anomaly_count,
    correlation_method,
    impact_score,
    root_cause,
    root_cause_confidence,
    remediation_plan,
    diagnosis_timestamp,
    llm_model,
    created_at,
    updated_at,
        CASE
            WHEN (root_cause IS NOT NULL) THEN 'DIAGNOSED'::text
            WHEN ((diagnosis_timestamp IS NOT NULL) AND (root_cause IS NULL)) THEN 'DIAGNOSIS_FAILED'::text
            ELSE 'PENDING_DIAGNOSIS'::text
        END AS diagnosis_status,
        CASE
            WHEN (diagnosis_timestamp IS NOT NULL) THEN EXTRACT(epoch FROM (diagnosis_timestamp - created_at))
            ELSE NULL::numeric
        END AS diagnosis_delay_seconds
   FROM public.incidents i;


ALTER VIEW public.incidents_with_diagnosis OWNER TO noc_admin;

--
-- Name: VIEW incidents_with_diagnosis; Type: COMMENT; Schema: public; Owner: noc_admin
--

COMMENT ON VIEW public.incidents_with_diagnosis IS 'Incidents enriched with diagnosis status';


--
-- Name: incidents incident_number; Type: DEFAULT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incidents ALTER COLUMN incident_number SET DEFAULT nextval('public.incidents_incident_number_seq'::regclass);


--
-- Data for Name: incident_anomalies; Type: TABLE DATA; Schema: public; Owner: noc_admin
--

COPY public.incident_anomalies (id, incident_id, anomaly_id, device_id, anomaly_type, detection_method, confidence, "timestamp", anomaly_data, created_at) FROM stdin;
2cf50fa6-99e8-44ce-ad3f-17bf5b032732	9e21086c-3a89-4c72-bb7e-135734da64c3	2026-04-25T20:23:45.106585	core-router-01	BGP_INSTABILITY	rule	1.00	2026-04-25 20:23:45.106585	{"details": "BGP session flapping: 2 state changes in 5 minutes", "severity": "HIGH", "device_id": "core-router-01", "timestamp": "2026-04-25T20:23:45.106585", "confidence": 1.0, "source_log": {"message": "%BGP-5-ADJCHANGE: neighbor 10.0.1.2 changed state to Idle", "severity": "CRITICAL", "bgp_state": "Idle", "device_id": "core-router-01", "timestamp": "Apr 25 20:23:45", "event_type": "BGP_STATE_CHANGE", "device_type": "router", "bgp_neighbor": "10.0.1.2"}, "detected_at": "2026-04-25T20:23:45.106628", "anomaly_type": "BGP_INSTABILITY", "bgp_neighbor": "10.0.1.2", "window_minutes": 5, "detection_method": "rule", "detector_version": "1.0.0", "state_change_count": 2}	2026-04-25 20:24:16.210051
b68f1fcc-8cdd-486b-b02d-695420f5f9a8	9e21086c-3a89-4c72-bb7e-135734da64c3	2026-04-25T20:24:16.144570	core-router-01	INTERFACE_FLAPPING	rule	1.00	2026-04-25 20:24:16.14457	{"details": "Interface changed state 2 times in 5 minutes", "severity": "HIGH", "device_id": "core-router-01", "interface": "GigabitEthernet0/2", "timestamp": "2026-04-25T20:24:16.144570", "confidence": 1.0, "source_log": {"message": "%LINK-3-UPDOWN: Interface changed state to down", "severity": "ERROR", "device_id": "core-router-01", "interface": "GigabitEthernet0/2", "timestamp": "Apr 25 20:24:16", "event_type": "INTERFACE_DOWN", "device_type": "router"}, "detected_at": "2026-04-25T20:24:16.144620", "event_count": 2, "anomaly_type": "INTERFACE_FLAPPING", "window_minutes": 5, "detection_method": "rule", "detector_version": "1.0.0"}	2026-04-25 20:24:16.210062
1e62f5a1-8d41-4dc7-9a6b-60aaa67f70ee	6dd1254c-2454-4ba0-893c-de73e4f34f76	2026-04-25T21:23:58.709118	core-router-01	INTERFACE_FLAPPING	rule	1.00	2026-04-25 21:23:58.709118	{"details": "Interface changed state 2 times in 5 minutes", "severity": "HIGH", "device_id": "core-router-01", "interface": "GigabitEthernet0/1", "timestamp": "2026-04-25T21:23:58.709118", "confidence": 1.0, "source_log": {"message": "%LINK-3-UPDOWN: Interface changed state to down", "severity": "ERROR", "device_id": "core-router-01", "interface": "GigabitEthernet0/1", "timestamp": "Apr 25 21:23:58", "event_type": "INTERFACE_DOWN", "device_type": "router"}, "detected_at": "2026-04-25T21:23:58.709484", "event_count": 2, "anomaly_type": "INTERFACE_FLAPPING", "window_minutes": 5, "detection_method": "rule", "detector_version": "1.0.0"}	2026-04-25 21:24:08.026006
a7ab7467-7d21-422b-8167-6d41dd6882e2	6dd1254c-2454-4ba0-893c-de73e4f34f76	2026-04-25T21:24:07.726488	core-router-01	INTERFACE_FLAPPING	rule	1.00	2026-04-25 21:24:07.726488	{"details": "Interface changed state 2 times in 5 minutes", "severity": "HIGH", "device_id": "core-router-01", "interface": "GigabitEthernet0/4", "timestamp": "2026-04-25T21:24:07.726488", "confidence": 1.0, "source_log": {"message": "%LINK-3-UPDOWN: Interface changed state to up", "severity": "INFO", "device_id": "core-router-01", "interface": "GigabitEthernet0/4", "timestamp": "Apr 25 21:24:07", "event_type": "INTERFACE_UP", "device_type": "router"}, "detected_at": "2026-04-25T21:24:07.726540", "event_count": 2, "anomaly_type": "INTERFACE_FLAPPING", "window_minutes": 5, "detection_method": "rule", "detector_version": "1.0.0"}	2026-04-25 21:24:08.026015
\.


--
-- Data for Name: incident_diagnosis_history; Type: TABLE DATA; Schema: public; Owner: noc_admin
--

COPY public.incident_diagnosis_history (id, incident_id, diagnosis_version, root_cause, root_cause_confidence, remediation_plan, llm_model, llm_prompt, llm_response, tokens_used, diagnosis_duration_ms, diagnosis_metadata, created_at) FROM stdin;
\.


--
-- Data for Name: incident_timeline; Type: TABLE DATA; Schema: public; Owner: noc_admin
--

COPY public.incident_timeline (id, incident_id, event_type, description, previous_status, new_status, changed_by, event_metadata, created_at) FROM stdin;
ceebf8b3-98d7-4d23-b4c0-8e6a3437f42b	9e21086c-3a89-4c72-bb7e-135734da64c3	CREATED	Incident created with 2 anomaly(ies) via PATTERN_BASED	\N	\N	SYSTEM	{}	2026-04-25 20:24:16.217806
61cae626-7f11-4f8a-9421-74944df4fc26	6dd1254c-2454-4ba0-893c-de73e4f34f76	CREATED	Incident created with 2 anomaly(ies) via TIME_BASED	\N	\N	SYSTEM	{}	2026-04-25 21:24:08.032116
\.


--
-- Data for Name: incident_type_definitions; Type: TABLE DATA; Schema: public; Owner: noc_admin
--

COPY public.incident_type_definitions (incident_type, description, typical_symptoms, recommended_actions) FROM stdin;
NETWORK_PERFORMANCE	Network-wide performance degradation	Multiple devices showing HIGH_CPU, HIGH_MEMORY, or packet loss	Check network utilization, investigate routing issues, verify QoS configuration
SECURITY_BREACH	Security incident or attack attempt	Multiple AUTH_FAILURE, UNAUTHORIZED_ACCESS events	Block attacking IPs, review firewall rules, check for compromised credentials
CONNECTIVITY_ISSUE	Network connectivity problems	Multiple INTERFACE_DOWN, BGP_DOWN, link failures	Check physical connections, verify routing protocols, inspect interface status
DEVICE_FAILURE	Single device experiencing multiple issues	Single device with various anomaly types	Investigate device health, check logs, consider device replacement or reboot
CASCADE_FAILURE	Upstream failure causing downstream impact	Upstream device failure affecting connected devices	Identify root cause device, restore upstream service first
UNKNOWN	Unclassified incident requiring investigation	Pattern not matching known incident types	Manual investigation required, gather more data
\.


--
-- Data for Name: incidents; Type: TABLE DATA; Schema: public; Owner: noc_admin
--

COPY public.incidents (id, incident_number, incident_type, severity, status, affected_device_count, affected_devices, primary_device, anomaly_count, start_time, end_time, duration_seconds, correlation_method, correlation_confidence, impact_score, root_cause, remediation_plan, incident_metadata, created_at, updated_at, resolved_at, root_cause_confidence, diagnosis_timestamp, llm_model, diagnosis_metadata) FROM stdin;
9e21086c-3a89-4c72-bb7e-135734da64c3	1	DEVICE_FAILURE	HIGH	ACTIVE	1	["core-router-01"]	core-router-01	2	2026-04-25 20:23:45.106585	\N	\N	PATTERN_BASED	75.00	38.00	The primary cause of this incident appears to be a combination of environmental stress and potential hardware failure. The high impact score suggests that the anomalies are affecting critical network operations.	[{"priority": "IMMEDIATE", "step": 1, "action": "Check environmental conditions (temperature and power supply) on core-router-01", "command": "", "expected_outcome": "Temperature within normal operating range; stable power supply.", "duration_minutes": 2}, {"priority": "IMMEDIATE", "step": 2, "action": "Perform a hardware diagnostic on the NIC and memory of core-router-01 using built-in CLI commands or external tools if necessary.", "command": "", "expected_outcome": "No critical errors found; all components functioning within specifications", "duration_minutes": 5}, {"priority": "SHORT_TERM", "step": 3, "action": "Review and validate configuration changes made to core-router-01 in the last 24 hours.", "command": "", "expected_outcome": "No recent erroneous configurations that could cause instability or interface issues", "duration_minutes": 5}, {"priority": "SHORT_TERM", "step": 4, "action": "Restart core-router-01 to clear potential transient software glitches.", "command": "", "expected_outcome": "Router returns to stable state with BGP and interface performance restored", "duration_minutes": 2}, {"priority": "LONG-TERM", "step": 5, "action": "Implement environmental monitoring for core devices.", "command": "", "expected_outcome": "Proactive alerts to prevent future incidents due to similar issues."}]	{"anomaly_count": 2, "correlation_timestamp": "2026-04-25T20:24:16.150847"}	2026-04-25 20:24:16.202901	2026-04-25 21:15:57.491032	\N	0.85	2026-04-25 21:15:57.491032	phi3	{"model": "phi3", "provider": "openai", "duration_ms": 319933, "response_id": "chatcmpl-946", "total_tokens": 2081, "finish_reason": "stop", "prompt_tokens": 1360, "completion_tokens": 721, "estimated_cost_usd": 0.0}
6dd1254c-2454-4ba0-893c-de73e4f34f76	2	UNKNOWN	HIGH	ACTIVE	1	["core-router-01"]	core-router-01	2	2026-04-25 21:23:58.709118	\N	\N	TIME_BASED	70.00	38.00	The primary cause appears to be an issue with the physical layer, specifically a potential hardware fault in GigabitEthernet0/1 and possibly related components affecting other interfaces due to shared media.	[{"priority": "IMMEDIATE", "step": 1, "action": "Physically inspect the GigabitEthernet0/1 and related hardware components for visible signs of damage or misalignment.", "command": "", "expected_outcome": "No physical faults found that could cause interface flapping", "duration_minutes": 2}, {"priority": "IMMEDIATE", "step": 2, "action": "Check for electromagnetic interference sources near the affected devices.", "command": "", "expected_outcome": "No external EMI source found that could affect network hardware performance", "duration_minutes": 3}, {"priority": "SHORT_TERM", "step": 1, "action": "Replace GigabitEthernet0/1 and related components if physical inspection reveals issues.", "command": "", "expected_outcome": "Interface shows 'up' status after replacement", "duration_minutes": 25}, {"priority": "SHORT_TERM", "step": 2, "action": "Perform a network trace to identify if the issue is isolated or affecting other devices.", "command": "", "expected_outcome": "Isolated flapping on GigabitEthernet0/1 with no impact on others", "duration_minutes": 5}, {"priority": "SHORT_TERM", "step": 3, "action": "Review and adjust the network layout to minimize shared resources between critical devices.", "command": "", "expected_outcome": "Reduced likelihood of cascading failures due to physical layer issues in future incidents", "duration_minutes": 15}, {"priority": "LONG-TERM", "step": 1, "action": "Schedule regular inspections of network hardware for signs of wear or potential EMI sources.", "command": "", "expected_outcome": "Proactive identification and mitigation of physical layer issues before they impact the network", "duration_minutes": 60}, {"priority": "LONG-TERM", "step": 2, "action": "Implement additional shielding and ground planes to protect against EMI.", "command": "", "expected_outcome": "Reduced risk of electromagnetic interference affecting network hardware performance", "duration_minutes": 30}]	{"anomaly_count": 2, "correlation_timestamp": "2026-04-25T21:24:07.950601"}	2026-04-25 21:24:08.015519	2026-04-25 21:40:00.587055	\N	0.95	2026-04-25 21:40:00.587055	phi3	{"model": "phi3", "provider": "openai", "duration_ms": 131526, "response_id": "chatcmpl-439", "total_tokens": 2391, "finish_reason": "stop", "prompt_tokens": 1246, "completion_tokens": 1145, "estimated_cost_usd": 0.0}
\.


--
-- Name: incidents_incident_number_seq; Type: SEQUENCE SET; Schema: public; Owner: noc_admin
--

SELECT pg_catalog.setval('public.incidents_incident_number_seq', 1, false);


--
-- Name: incident_anomalies incident_anomalies_pkey; Type: CONSTRAINT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incident_anomalies
    ADD CONSTRAINT incident_anomalies_pkey PRIMARY KEY (id);


--
-- Name: incident_diagnosis_history incident_diagnosis_history_incident_id_diagnosis_version_key; Type: CONSTRAINT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incident_diagnosis_history
    ADD CONSTRAINT incident_diagnosis_history_incident_id_diagnosis_version_key UNIQUE (incident_id, diagnosis_version);


--
-- Name: incident_diagnosis_history incident_diagnosis_history_pkey; Type: CONSTRAINT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incident_diagnosis_history
    ADD CONSTRAINT incident_diagnosis_history_pkey PRIMARY KEY (id);


--
-- Name: incident_timeline incident_timeline_pkey; Type: CONSTRAINT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incident_timeline
    ADD CONSTRAINT incident_timeline_pkey PRIMARY KEY (id);


--
-- Name: incident_type_definitions incident_type_definitions_pkey; Type: CONSTRAINT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incident_type_definitions
    ADD CONSTRAINT incident_type_definitions_pkey PRIMARY KEY (incident_type);


--
-- Name: incidents incidents_incident_number_key; Type: CONSTRAINT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incidents
    ADD CONSTRAINT incidents_incident_number_key UNIQUE (incident_number);


--
-- Name: incidents incidents_pkey; Type: CONSTRAINT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incidents
    ADD CONSTRAINT incidents_pkey PRIMARY KEY (id);


--
-- Name: incident_anomalies unique_incident_anomaly; Type: CONSTRAINT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incident_anomalies
    ADD CONSTRAINT unique_incident_anomaly UNIQUE (incident_id, anomaly_id);


--
-- Name: idx_diagnosis_history_created; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_diagnosis_history_created ON public.incident_diagnosis_history USING btree (created_at DESC);


--
-- Name: idx_diagnosis_history_incident; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_diagnosis_history_incident ON public.incident_diagnosis_history USING btree (incident_id);


--
-- Name: idx_diagnosis_history_model; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_diagnosis_history_model ON public.incident_diagnosis_history USING btree (llm_model);


--
-- Name: idx_incident_anomalies_device; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_incident_anomalies_device ON public.incident_anomalies USING btree (device_id);


--
-- Name: idx_incident_anomalies_incident; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_incident_anomalies_incident ON public.incident_anomalies USING btree (incident_id);


--
-- Name: idx_incident_anomalies_timestamp; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_incident_anomalies_timestamp ON public.incident_anomalies USING btree ("timestamp" DESC);


--
-- Name: idx_incidents_affected_devices; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_incidents_affected_devices ON public.incidents USING gin (affected_devices);


--
-- Name: idx_incidents_created_at; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_incidents_created_at ON public.incidents USING btree (created_at DESC);


--
-- Name: idx_incidents_diagnosis_timestamp; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_incidents_diagnosis_timestamp ON public.incidents USING btree (diagnosis_timestamp DESC);


--
-- Name: idx_incidents_root_cause_confidence; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_incidents_root_cause_confidence ON public.incidents USING btree (root_cause_confidence DESC);


--
-- Name: idx_incidents_severity; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_incidents_severity ON public.incidents USING btree (severity);


--
-- Name: idx_incidents_start_time; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_incidents_start_time ON public.incidents USING btree (start_time DESC);


--
-- Name: idx_incidents_status; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_incidents_status ON public.incidents USING btree (status);


--
-- Name: idx_incidents_type; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_incidents_type ON public.incidents USING btree (incident_type);


--
-- Name: idx_timeline_created; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_timeline_created ON public.incident_timeline USING btree (created_at DESC);


--
-- Name: idx_timeline_incident; Type: INDEX; Schema: public; Owner: noc_admin
--

CREATE INDEX idx_timeline_incident ON public.incident_timeline USING btree (incident_id);


--
-- Name: incidents trigger_incident_duration; Type: TRIGGER; Schema: public; Owner: noc_admin
--

CREATE TRIGGER trigger_incident_duration BEFORE UPDATE ON public.incidents FOR EACH ROW EXECUTE FUNCTION public.calculate_incident_duration();


--
-- Name: incidents trigger_incidents_updated_at; Type: TRIGGER; Schema: public; Owner: noc_admin
--

CREATE TRIGGER trigger_incidents_updated_at BEFORE UPDATE ON public.incidents FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: incidents trigger_log_status_change; Type: TRIGGER; Schema: public; Owner: noc_admin
--

CREATE TRIGGER trigger_log_status_change AFTER UPDATE ON public.incidents FOR EACH ROW WHEN (((old.status)::text IS DISTINCT FROM (new.status)::text)) EXECUTE FUNCTION public.log_incident_status_change();


--
-- Name: incident_anomalies incident_anomalies_incident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incident_anomalies
    ADD CONSTRAINT incident_anomalies_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES public.incidents(id) ON DELETE CASCADE;


--
-- Name: incident_diagnosis_history incident_diagnosis_history_incident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incident_diagnosis_history
    ADD CONSTRAINT incident_diagnosis_history_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES public.incidents(id) ON DELETE CASCADE;


--
-- Name: incident_timeline incident_timeline_incident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: noc_admin
--

ALTER TABLE ONLY public.incident_timeline
    ADD CONSTRAINT incident_timeline_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES public.incidents(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict I8R2nJoN1JJGd1u93owDXwsELHPgh23QogtNg2SaikH86IeboVrT6DJRMIJ9WsN

