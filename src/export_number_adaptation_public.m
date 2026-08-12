function audit = export_number_adaptation_public(input_path, output_path)
%EXPORT_NUMBER_ADAPTATION_PUBLIC Create the outcome-blind public trial view.
%
% The exported file deliberately contains no reference, test, or adapter
% numerosity.  Exact stimulus triples receive opaque identifiers in stable
% first-occurrence order.  Equality trials are excluded because the frozen
% later loss has no unique physical answer for them.

source = load(input_path, 'out');
if ~isfield(source, 'out') || ~iscell(source.out) || numel(source.out) ~= 30
    error('number_adaptation:invalidSource', ...
        'Expected a 30-participant cell array named out.');
end

parent = fileparts(output_path);
if ~isempty(parent) && ~exist(parent, 'dir')
    mkdir(parent);
end
fid = fopen(output_path, 'w');
if fid < 0
    error('number_adaptation:outputOpen', 'Cannot open public output file.');
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, 'record_order,participant_id,task_id,response,cost_seconds\n');

task_ids = containers.Map('KeyType', 'char', 'ValueType', 'double');
next_task_id = 1;
record_order = 0;
raw_trial_count = 0;
equality_excluded = 0;

required = {'reference_n','test_n','adapter_n','response','confidence','RT'};
expected_heights = [240 270 240 270 270 270 320 400 400 350 ...
    400 400 400 400 400 400 400 400 400 400 480 120 480 480 ...
    480 480 480 480 480 480];
for participant = 1:numel(source.out)
    item = source.out{participant};
    if ~isstruct(item) || ~isfield(item, 'data') || ~istable(item.data)
        error('number_adaptation:invalidParticipant', ...
            'Each participant must contain one MATLAB table named data.');
    end
    data = item.data;
    if height(data) ~= expected_heights(participant) || width(data) ~= 6 || ...
            ~isequal(data.Properties.VariableNames, required)
        error('number_adaptation:invalidTable', ...
            'Unexpected participant table shape or variable order.');
    end
    raw_trial_count = raw_trial_count + height(data);
    for trial = 1:height(data)
        reference = double(data.reference_n(trial));
        test = double(data.test_n(trial));
        adapter = double(data.adapter_n(trial));
        response = double(data.response(trial));
        seconds = double(data.RT(trial));
        if ~isscalar(reference) || reference ~= 12
            error('number_adaptation:reference', ...
                'Reference numerosity violates the public codebook.');
        end
        if ~isscalar(test) || ~isfinite(test) || test ~= fix(test) || ...
                test < 5 || test > 200
            error('number_adaptation:test', ...
                'Test numerosity violates the public paper range.');
        end
        if ~isscalar(adapter) || ~ismember(adapter, [0 6 24])
            error('number_adaptation:adapter', ...
                'Adapter numerosity violates the public codebook.');
        end
        if ~isscalar(response) || ~ismember(response, [0 1])
            error('number_adaptation:response', ...
                'Response must use the documented binary vocabulary.');
        end
        if ~isscalar(seconds) || ~isfinite(seconds) || seconds <= 0
            error('number_adaptation:time', ...
                'Reaction time must be positive and finite.');
        end
        if test == reference
            equality_excluded = equality_excluded + 1;
            continue;
        end
        key = sprintf('%.0f|%.0f|%.0f', reference, test, adapter);
        if ~isKey(task_ids, key)
            task_ids(key) = next_task_id;
            next_task_id = next_task_id + 1;
        end
        record_order = record_order + 1;
        fprintf(fid, '%d,%d,T%04d,%d,%.17g\n', record_order, participant, ...
            task_ids(key), response, seconds);
    end
end

audit = struct();
audit.participant_count = numel(source.out);
audit.raw_trial_count = raw_trial_count;
audit.equality_trial_count_excluded_without_value_export = equality_excluded;
audit.exported_trial_count = record_order;
audit.opaque_task_count = next_task_id - 1;
audit.truth_values_exported = false;
audit.stimulus_values_exported = false;
end
