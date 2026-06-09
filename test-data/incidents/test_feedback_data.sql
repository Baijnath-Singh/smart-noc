-- Add sample feedback for testing calibration
-- Date: 2026-06-09

-- Scenario 1: High confidence (0.9) but only 60% accuracy (overconfident)
INSERT INTO diagnosis_feedback (diagnosis_id, incident_number, llm_confidence, predicted_root_cause, incident_type, was_correct, engineer_id)
VALUES 
(gen_random_uuid(), 60, 0.9, 'VLAN misconfiguration', 'CONNECTIVITY_ISSUE', true, 'engineer1'),
(gen_random_uuid(), 61, 0.9, 'VLAN misconfiguration', 'CONNECTIVITY_ISSUE', false, 'engineer1'),
(gen_random_uuid(), 62, 0.9, 'VLAN misconfiguration', 'CONNECTIVITY_ISSUE', true, 'engineer1'),
(gen_random_uuid(), 66, 0.9, 'VLAN misconfiguration', 'CONNECTIVITY_ISSUE', false, 'engineer1'),
(gen_random_uuid(), 67, 0.9, 'VLAN misconfiguration', 'CONNECTIVITY_ISSUE', false, 'engineer1');

-- Scenario 2: Moderate confidence (0.7) but 100% accuracy (underconfident)
INSERT INTO diagnosis_feedback (diagnosis_id, incident_number, llm_confidence, predicted_root_cause, incident_type, was_correct, engineer_id)
VALUES 
(gen_random_uuid(), 58, 0.7, 'VLAN misconfiguration', 'CONNECTIVITY_ISSUE', true, 'engineer2'),
(gen_random_uuid(), 59, 0.7, 'VLAN misconfiguration', 'CONNECTIVITY_ISSUE', true, 'engineer2'),
(gen_random_uuid(), 68, 0.7, 'VLAN misconfiguration', 'CONNECTIVITY_ISSUE', true, 'engineer2');

-- Check inserted data
SELECT COUNT(*) as total_feedback, 
       SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct_count,
       AVG(llm_confidence) as avg_confidence
FROM diagnosis_feedback;

-- Show calibration metrics by bucket
SELECT * FROM confidence_calibration_metrics ORDER BY confidence_bucket DESC;

-- Show overall calibration status
SELECT * FROM calibration_status;
