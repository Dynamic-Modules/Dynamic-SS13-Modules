/datum/unit_test/dynamic_module_trip_system_exists/Run()
	var/datum/dynamic_module_trip_system/trips = new
	TEST_ASSERT(!isnull(trips), "trip system datum should instantiate")

